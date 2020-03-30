class MetricFilters:
    def __init__(self):
        self.metric_filters = []

    def add_filter(
        self, filter_name, filter_pattern, log_group_name, metric_transformations
    ):
        self.metric_filters.append(
            {
                "filterName": filter_name,
                "filterPattern": filter_pattern,
                "logGroupName": log_group_name,
                "metricTransformations": metric_transformations,
            }
        )

    def get_matching_filters(
        self, prefix=None, log_group_name=None, metric_name=None, metric_namespace=None
    ):
        assert (
            metric_name is None
            and metric_namespace is None
            or metric_name is not None
            and metric_namespace is not None
        )

        result = []
        for f in self.metric_filters:
            prefix_matches = prefix is None or f["filterName"].startswith(prefix)
            log_group_matches = (
                log_group_name is None or f["logGroupName"] == log_group_name
            )
            metric_name_matches = (
                metric_name is None
                or f["metricTransformations"]["metricName"] == metric_name
            )
            namespace_matches = (
                metric_namespace is None
                or f["metricTransformations"]["metricNamespace"] == metric_namespace
            )

            if (
                prefix_matches
                and log_group_matches
                and metric_name_matches
                and namespace_matches
            ):
                result.append(f)

        return result

    def delete_filter(self, filter_name=None, log_group_name=None):
        for f in self.metric_filters:
            if f["filterName"] == filter_name and f["logGroupName"] == log_group_name:
                self.metric_filters.remove(f)
        return self.metric_filters
