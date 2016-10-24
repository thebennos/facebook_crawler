from elasticsearch import Elasticsearch
from elasticsearch import helpers
import simplejson as json
import logging
import traceback

class wrapper():
    FORMAT = '[%(asctime)s -- %(levelname)s -- %(threadName)s -- %(funcName)s]:%(message)s'
    logging.basicConfig(format=FORMAT)
    logger = logging.getLogger("fb_wrapper")

    def __init__(self, es_server, index):
        self.es = Elasticsearch([es_server])
        self.index = index

    #put page data to elasticsearch
    def fb_page_wrapper(self, page_data):
        doc = {}
        doc['fan_count'] = page_data['fan_count']
        doc['about'] = page_data['about']
        doc['category'] = page_data['category']
        doc['picture'] = page_data['picture']['data']['url']
        try:
            response = self.es.index(index = self.index, doc_type = 'page', id = page_data['id'], body = doc)
            return  True
        except Exception, error:
            self.logger.warning(error)
            return False

    def fb_post_wrapper(self, posts_data, page_id):
        actions = []
        for post_data in posts_data:
            try:
                action = {}
                action['_id'] = post_data['id'].split("_")[1]
                action['_index'] = self.index
                action['_type'] = 'posts'
                action['parent'] = page_id
                action['created_time'] = post_data['created_time']
                action['updated_time'] = post_data['updated_time']
                action['type'] = post_data['type']
                action['status_type'] = post_data['status_type']
                action['uid'] = post_data['id']
                if post_data.has_key('message'):
                    action['message'] = post_data['message']
                if post_data.has_key('shares'):
                    action['shares'] = post_data['shares']['count']
                actions.append(action)
            except Exception, error:
                traceback.print_exc()
                self.logger.error("Bulk Put Document to ES : {1}".format(json.dumps(post_data)))
        helpers.bulk(self.es, actions, request_timeout=120)

    def fb_comments_wrapper(self, comments_data, post_id):
        actions = []
        for comment_data in comments_data:
            try:
                action = {}
                action['_id'] = comment_data['id'].split("_")[1]
                action['_index'] = self.index
                action['_type'] = 'comments'
                action['parent'] = post_id
                action['created_time'] = comment_data['created_time']
                action['uid'] = comment_data['id']
                if comment_data.has_key('message'):
                    action['message'] = comment_data['message']
                action["like_count"] = comment_data["like_count"]
                action["comment_count"] = comment_data['comment_count']
                action["from_name"] = comment_data["from"]["name"]
                action["from_id"] = comment_data["from"]["id"]
                if comment_data.has_key("attachment"):
                    if comment_data["attachment"].has_key("description"):
                        action["attachment"]["description"] = comment_data["attachment"]["description"]
                    if comment_data["attachment"].has_key("title"):
                        action["attachment"]["title"] = comment_data["attachment"]["title"]
                    if comment_data["attachment"].has_key("media"):
                        action["attachment"]["image_url"] = comment_data["attachment"]["media"]["image"]["src"]
                    action["attachment"]["target_url"] = comment_data["attachment"]["url"]
                actions.append(action)
            except Exception, error:
                traceback.print_exc()
                self.logger.error("Bulk Put comment to ES : {0}".format(json.dumps(comment_data)))
        helpers.bulk(self.es, actions, request_timeout=120)