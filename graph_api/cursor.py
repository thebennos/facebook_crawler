from elasticsearch import Elasticsearch
import logging
import simplejson as json
from dateutil.parser import parse
import datetime

class cursor():

    logger = logging.getLogger("fb_wrapper")

    def __init__(self, es_server, es_index, page_id):
        self.es = Elasticsearch([es_server])
        self.page_id = page_id
        self.index = es_index
    #get newest events in es
    def get_newest_event(self):
        posts_query_json = {"_source": ["start_time"],
                            "query":
                                {"bool":
                                     {"filter":
                                          [{"term": {"_type": "events"}},
                                           {"term": {"parent": self.page_id}}
                                           ]
                                      }
                                 },
                            "sort": [{"start_time": {"order": "desc"}}],
                            "size": 1, "from": 0
                            }
        response = self.es.search(index=self.index, doc_type="events", body=posts_query_json)

        #No Posts in ES
        if len(response['hits']['hits']) == 0:
            one_year_ago = datetime.datetime.now() - datetime.timedelta(days=1 * 365)
            return one_year_ago

        # Found the last newest post get newer
        for doc in response['hits']['hits']:
            last_new_date = doc['_source']['start_time']
            self.logger.debug("name:{0} fetch oldeset post {1}".format(self.page_id, last_new_date))
            return parse(last_new_date)

    # Scan  the newest posts in our ES relative to this page
    def get_newest_posts(self):
        posts_query_json = {"_source": ["uid", "created_time"],
                            "query":
                                {"bool":
                                     {"filter":
                                          [{"term": {"_type": "posts"}},
                                           {"term": {"parent": self.page_id}}
                                           ]
                                      }
                                 },
                            "sort": [{"created_time": {"order": "desc"}}],
                            "size": 1, "from": 0
                            }
        response = self.es.search(index=self.index, doc_type="posts", body=posts_query_json)

        #No Posts in ES
        if len(response['hits']['hits']) == 0:
            one_year_ago = datetime.datetime.now() - datetime.timedelta(days=1 * 365)
            return one_year_ago

        # Found the last newest post get newer
        for doc in response['hits']['hits']:
            print("%s) %s" % (doc['_id'], doc['_source']['created_time']))
            last_new_date = doc['_source']['created_time']
            self.logger.debug("name:{0} fetch oldeset post {1}".format(self.page_id, last_new_date))
            return parse(last_new_date)

    # Scan all the posts and newest comments to every post, return posts--timestamp
    def get_newest_comments(self, query_index):
        query_json= { "_source" : ["uid", "created_time"],
                      "query" :
                          { "bool":
                                { "filter":
                                      [ { "term": { "_type": "posts"   }},
                                        { "term": { "parent": self.page_id }}
                                        ]
                                  }
                            },
                      "sort" : [{"created_time":{"order":"desc"}}],
                      "size":30, "from": query_index
                      }

        #result  postsid : timestamp
        result = []
        # multi search
        search_arr = []
        query_json["from"] = query_index

        res = self.es.search(index=self.index, doc_type="posts", body=query_json)

        for doc in res['hits']['hits']:
            print("%s) %s" % (doc['_source']['uid'], doc['_source']['created_time']))
            search_arr.append({'index': self.index, 'type': 'comments'})
            search_arr.append({"query": {"term" : {"parent" : doc['_source']['uid']}},
                               'from': 0, 'size': 1, "_source":["created_time", "parent"],
                               "sort" : [{"created_time":{"order":"desc"}}]})
        #multi search
        request = ''
        for each in search_arr:
            request += '%s \n' % json.dumps(each)
        resp = self.es.msearch(body=request)

        i = 0
        for response in resp['responses']:
            if response['hits']['total'] == 0:
                result.append({"post_id" : res['hits']['hits'][i]['_source']['uid'], "end_time" : 0})
            else:
                for comment_doc in response['hits']['hits']:
                    lastNewDate = comment_doc['_source']['created_time']
                    result.append({"post_id" : comment_doc['_source']['parent'], "end_time" : parse(lastNewDate)})
            i = i + 1

        return result
