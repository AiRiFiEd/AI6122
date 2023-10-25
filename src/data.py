import logging
logger = logging.getLogger(__name__)

import os
import pickle
from typing import Dict, List
from collections import defaultdict
import hashlib
import lxml.etree
import datetime

class Entity(object):
    def __init__(self) -> None:
        self.tag = ''
        self.relationships = dict()

    def __repr__(self) -> str:
        args = []
        for k, v in self.__dict__.items():
            args.append(str(k) + '=' + str(v))
        return 'Entity({args})'.format(
            args=','.join(args)
        )
    
    def __str__(self) -> str:
        return self.__repr__()
    
    @property
    def hash(self) -> str:
        return hashlib.sha256(self.__repr__().encode('utf-8')).hexdigest()

    def from_element(self, node: lxml.etree._Element) -> None:
        """
        Instantiates entity object with attributes from an Element object

        Parameters
        ----------
        node : lxml.etree._Element
        """
        self.tag = node.tag
        for attribute in node.items():
            setattr(self, attribute[0], attribute[1])

        for sub in node:
            self.relationships[sub.text] = sub.tag

class DatasetCustom(object):
    def __init__(self) -> None:
        pass

class DatasetDBLP(DatasetCustom):
    # https://github.com/26hzhang/DBLPParser
    # https://github.com/26hzhang/DBLPParser/blob/master/src/dblp_parser.py#L76
    # https://www.andyfitzgeraldconsulting.com/writing/keyword-extraction-nlp/

    _ELEMENTS = 'article|inproceedings|proceedings|book|incollection|phdthesis|mastersthesis|www|person|data'
    _ENTITIES = 'author|editor|title|booktitle|pages|year|address|journal|volume|number|month|url|ee|cdrom|cite|publisher|note|crossref|isbn|series|school|chapter|publnr|stream|rel'

    def __init__(self, directory_output: str) -> None:
        super().__init__()
        self.directory_output = directory_output
        self.uid = hashlib.sha256(str(datetime.datetime.now().timestamp()).encode('utf-8')).hexdigest()
        self.source = None
        self.data = None

        self.entities = defaultdict(list)
        self.entities_idx_by_tag = defaultdict(int)
        self.entities_idx_by_key = defaultdict(lambda:defaultdict(list))

        self.attributes_by_tag = defaultdict(lambda:defaultdict(int))
        self.relationships_by_tag = defaultdict(lambda:defaultdict(int))

    def from_file(self, filepath: str) -> None:

        self.data = lxml.etree.iterparse(
            source=filepath, 
            dtd_validation=True,
            load_dtd=True,
            huge_tree=True)

    def parse_data(self, elements_to_include: List=[], 
                        buffer_size: int=10000000) -> List[Dict]:
        if not self.data is None:
            elements = elements_to_include if elements_to_include else (self.available_elements + self.available_entities) 
            i = 0
            for _, element in self.data:                
                if element.tag in elements:
                    entity = Entity()
                    entity.from_element(element)
                    idx = len(self.entities[entity.tag])
                    self.entities[entity.tag].append(entity)

                    # index data
                    
                    self.entities_idx_by_tag[entity.tag] += 1
                    try:
                        self.entities_idx_by_key[entity.tag][entity.key].append(self.entities_idx_by_tag[entity.tag]-1)
                    except:
                        self.entities_idx_by_key[entity.tag][entity.hash].append(self.entities_idx_by_tag[entity.tag]-1)

                    # count attributes by tag
                    for k, v in entity.__dict__.items():
                        if k != 'relationships':
                            self.attributes_by_tag[entity.tag][v] += 1
                    
                    for k, v in entity.relationships.items():
                        self.relationships_by_tag[entity.tag][v] += 1

                    i += 1

                    # dump memory to file
                    if i > buffer_size:
                        for k, v in self.entities.items():
                            filepath = os.path.join(
                                self.directory_output, (k + '_' + self.uid + '.pkl')
                            )
                            if os.path.isfile(filepath):
                                with open(filepath, 'rb') as f:
                                    tmp = pickle.load(f)
                                tmp += v
                                with open(filepath, 'wb') as f:
                                    pickle.dump(tmp, f)
                                del tmp
                            else:
                                with open(filepath, 'wb') as f:
                                    pickle.dump(v, f)
                                
                        del self.entities
                        self.entities = defaultdict(list)

                        i = 0


                element.clear()
                while element.getprevious() is not None:
                    del element.getparent()[0]
        else:
            logger.error('no data loaded.')

    @property
    def available_elements(self) -> List:
        return self._ELEMENTS.split('|')    

    @property
    def available_entities(self) -> List:
        return self._ENTITIES.split('|')
    
        

