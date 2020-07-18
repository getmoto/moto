class TaggingService:
    def __init__(self, tagName="Tags", keyName="Key", valueName="Value"):
        self.tagName = tagName
        self.keyName = keyName
        self.valueName = valueName
        self.tags = {}

    def get_tag_dict_for_resource(self, arn):
        result = {}
        if self.has_tags(arn):
            for k, v in self.tags[arn].items():
                result[k] = v
        return result

    def list_tags_for_resource(self, arn):
        result = []
        if self.has_tags(arn):
            for k, v in self.tags[arn].items():
                result.append({self.keyName: k, self.valueName: v})
        return {self.tagName: result}

    def delete_all_tags_for_resource(self, arn):
        if self.has_tags(arn):
            del self.tags[arn]

    def has_tags(self, arn):
        return arn in self.tags

    def tag_resource(self, arn, tags):
        if arn not in self.tags:
            self.tags[arn] = {}
        for t in tags:
            if self.valueName in t:
                self.tags[arn][t[self.keyName]] = t[self.valueName]
            else:
                self.tags[arn][t[self.keyName]] = None

    def copy_tags(self, from_arn, to_arn):
        if self.has_tags(from_arn):
            self.tag_resource(
                to_arn, self.list_tags_for_resource(from_arn)[self.tagName]
            )

    def untag_resource_using_names(self, arn, tag_names):
        for name in tag_names:
            if name in self.tags.get(arn, {}):
                del self.tags[arn][name]

    def untag_resource_using_tags(self, arn, tags):
        m = self.tags.get(arn, {})
        for t in tags:
            if self.keyName in t:
                if t[self.keyName] in m:
                    if self.valueName in t:
                        if m[t[self.keyName]] != t[self.valueName]:
                            continue
                    # If both key and value are provided, match both before deletion
                    del m[t[self.keyName]]

    def extract_tag_names(self, tags):
        results = []
        if len(tags) == 0:
            return results
        for tag in tags:
            if self.keyName in tag:
                results.append(tag[self.keyName])
        return results

    def flatten_tag_list(self, tags):
        result = {}
        for t in tags:
            if self.valueName in t:
                result[t[self.keyName]] = t[self.valueName]
            else:
                result[t[self.keyName]] = None
        return result
