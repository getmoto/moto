def querystring_to_dict(querystring, namespace):
    data = []
    metricindex = 1
    while True:
        try:
            metric_name = querystring[
                'MetricData.member.{0}.MetricName'.format(metricindex)][0]
        except KeyError:
            break
        dictitem = querystring_parent_metrics(
            querystring, namespace, metric_name, metricindex)
        data.append(dictitem)
        metricindex += 1
    return data


def querystring_parent_metrics(querystring, namespace, metric_name, index):
    dictitem = {}

    metric_name = querystring['MetricData.member.{0}.MetricName'.format(
        index)][0]
    dictitem['MetricName'] = metric_name

    dimensions = querystring_dimensions(querystring, index)
    if (dimensions != []):
        dictitem['Dimensions'] = dimensions

    statistics = querystring_statistics(querystring, index)
    if (statistics != []):
        dictitem['Statistics'] = statistics

    value = querystring.get('MetricData.member.{0}.Value'.format(index), None)
    if value is not None:
        dictitem['Value'] = value[0]

    timestamp = querystring.get(
        'MetricData.member.{0}.Timestamp'.format(index), None)
    if timestamp is not None:
        dictitem['Timestamp'] = timestamp[0]

    unit = querystring.get('MetricData.member.{0}.Unit'.format(index), None)
    if unit is not None:
        dictitem['Unit'] = unit[0]

    resolution = querystring.get(
        'MetricData.member.{0}.StorageResolution'.format(index), None)
    if resolution is not None:
        dictitem['StorageResolution'] = resolution[0]

    return dictitem


def querystring_dimensions(querystring, metric_index):
    dimensions = []
    dimension_index = 1
    while True:
        try:
            dimension_name = querystring['MetricData.member.{0}.Dimensions.member.{1}.Name'.format(
                metric_index, dimension_index)][0]
        except KeyError:
            break
        dimension_value = querystring['MetricData.member.{0}.Dimensions.member.{1}.Value'.format(
            metric_index, dimension_index)][0]
        dimensions.append(
            {'Name': dimension_name, 'Value': dimension_value})
        dimension_index += 1
    return dimensions

# it looks like from the docs these are all required values


def querystring_statistics(querystring, metric_index):
    try:
        statcount = querystring['MetricData.member.{0}.StatisticValues.SampleCount'.format(
            metric_index)][0]
        statsum = querystring['MetricData.member.{0}.StatisticValues.Sum'.format(
            metric_index)][0]
        statmin = querystring['MetricData.member.{0}.StatisticValues.Minimum'.format(
            metric_index)][0]
        statmax = querystring['MetricData.member.{0}.StatisticValues.Maximum'.format(
            metric_index)][0]
    except KeyError:
        return None
    statisticvalues = {
        'SampleCount': statcount,
        'Sum': statsum,
        'Minumum': statmin,
        'Maximum': statmax
    }
    return statisticvalues
