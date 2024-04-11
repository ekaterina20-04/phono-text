from flask_restful import Api, Resource
from flask import jsonify
from posts import get_git_history



class TextVersions(Resource):
    def get(self,id):
        text_versions = get_git_history(fr"\articles\article_{id}")
        return jsonify(text_versions)


api = Api()


api.add_resource(TextVersions, '/<int:id>/get_file_history')
