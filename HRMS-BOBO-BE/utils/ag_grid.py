import logging

from utils.utils import hash_value
from django.db import connection

logger = logging.getLogger(__name__)


def buildSql(data, tablename, equalCond=None):
    return selectSql(data) + ' FROM ' + tablename + whereSql(data, equalCond) + groupBySql(data) + orderBySql(
        data) + limitSql(data)


def selectSql(data):
    rowGroupCols = data.get('rowGroupCols')
    valueCols = data.get('valueCols')
    groupKeys = data.get('groupKeys')

    if isDoingGrouping(rowGroupCols, groupKeys):
        rowGroupCol = rowGroupCols[len(groupKeys)]
        colsToSelect = [rowGroupCol['id']]

        for valueCol in valueCols:
            colsToSelect.append(valueCol['aggFunc'] + '(' + valueCol['id'] + ') AS ' + valueCol['id'])

        return 'SELECT COUNT(id) AS count,'.format(colsToSelect) + ', '.join(colsToSelect)

    return 'SELECT * '


def whereSql(data, eqcond=None):
    rowGroups = data.get('rowGroupCols')
    groupKeys = data.get('groupKeys')
    filterModel = data.get('filterModel')

    whereParts = []

    if groupKeys:
        for i, key in enumerate(groupKeys):
            value = "'" + key + "'" if type(key) == str else key
            whereParts.append(str(rowGroups[i]['id']) + ' = ' + str(value))

    if filterModel:
        for key, value in filterModel.items():
            if value['filterType'] == 'set':
                whereParts.append(key + " IN ('" + ', '.join(value['values']) + "')")

    if eqcond:
        whereParts.append(eqcond)
    if len(whereParts) > 0:
        return ' WHERE ' + ' AND '.join(whereParts)
    return ''


def groupBySql(data):
    rowGroupCols = data.get('rowGroupCols')
    groupKeys = data.get('groupKeys')

    if isDoingGrouping(rowGroupCols, groupKeys):
        rowGroupCol = rowGroupCols[len(groupKeys)]
        return ' GROUP BY ' + rowGroupCol['id']
    return ''


def orderBySql(data):
    sortModel = data.get('sortModel')

    if len(sortModel) == 0:
        return ''
    sorts = [s['colId'] + ' ' + s['sort'].upper() for s in sortModel]
    return ' ORDER BY ' + ",".join(sorts)


def limitSql(data):
    endRow = data.get('endRow')
    startRow = data.get('startRow')
    if (endRow is None or startRow is None):
        return ''

    blockSize = endRow - startRow

    return ' LIMIT ' + str(blockSize) + ' OFFSET ' + str(startRow)


def isDoingGrouping(rowGroupCols, groupKeys):
    # we are not doing grouping if at the lowest level
    return len(rowGroupCols) > len(groupKeys)


def executePivotColQuery(data, tablename):
    pivotCols = data.get('pivotCols')
    pivotCol = pivotCols[0]

    results = {}
    valueCols = data.get('valueCols')

    for valueCol in valueCols:
        pivotResults = executePivotQuery(data, pivotCol, valueCol, tablename)
        logger.info("pivotResults={0} ".format(pivotResults))
        logger.info("results={0}".format(results))

        for i, pivotResult in enumerate(pivotResults):
            result = results[i] if i in results else {}

            for key, value in pivotResult.items():
                result[key] = pivotResult[key]

            results[i] = result
    logger.info("executequery results ={0}".format(results))

    return {
        "results": list(results.values()),
        "lastRow": len(results),
        "pivotFields": getPivotFields(data, tablename)
    }


def executePivotQuery(data, pivotCol, valueCol, tablename):
    groupKeys = data.get('groupKeys')
    groupsToUse = data.get('rowGroupCols')[len(groupKeys):len(groupKeys) + 1]
    selectGroupCols = ", ".join([i['id'] for i in groupsToUse])

    sql = "SELECT  {0},  {1} || '_' || {2} AS {1},  SUM({2}) AS {2} FROM  (SELECT * FROM {3}) GROUP BY  {0}".format(
        selectGroupCols, pivotCol['id'], valueCol['id'], tablename) + whereSql(
        data) + orderBySql(data) + limitSql(data)
    sql = sql.replace("to_department", "to_department_id").replace("from_department", "from_department_id").replace(
        "resume", "resume_id")

    logger.info('inside 2 executePivotQuery sql query {0}'.format(sql))

    results = execute_sql_query(sql)
    return results


def getPivotFields(request, tablename):
    pivotCol = request.get('pivotCols')[0]
    results = []

    for valueCol in request.get('valueCols'):
        sql = "SELECT DISTINCT ({0} || '_' || {1}) AS {0} FROM {2} ORDER BY {0}".format(pivotCol['id'], valueCol['id'],
                                                                                        tablename)
        sql = sql.replace("to_department", "to_department_id").replace("from_department",
                                                                       "from_department_id")

        result = execute_sql_query(sql)
        logger.info("getPivotFields inside 1 sql {0}".format(sql))
        logger.info("getPivotFields for result={0}".format(result))
        results.append(result)
    logger.info("getPivotFields results ={0}".format(results))
    results = flatten_array(results)
    logger.info("results={0}".format(results))
    result = [i[pivotCol['id']] for i in results]
    return result


def handle_aggrid_input(request):
    start_row = request.POST.get('startRow')
    end_row = request.POST.get('endRow') if start_row else None
    row_group_cols = request.POST.get(
        'rowGroupCols')  # 'rowGroupCols': [{'id': 'interviewer_emp_id', 'displayName': 'Interviewer ID', 'field': 'interviewer_emp_id'}]
    value_cols = request.POST.get(
        'valueCols')  # [{'id': 'name', 'aggFunc': 'sum', 'displayName': 'Name', 'field': 'name'}]
    pivot_cols = request.POST.get('pivotCols')  # TODO Check validation in the future
    pivot_mode = request.POST.get('pivotMode', False)
    group_keys = request.POST.get('groupKeys')  # [1,23,'abc']
    filter_model = request.POST.get('filterModel')  # {'to_department': {'values': ['4', '3'], 'filterType': 'set'}}
    sort_model = request.POST.get('sortModel')  # [{'sort': 'desc', 'colId': 'status'}]

    valid_input = True
    if start_row and not str(start_row).isalnum():
        valid_input = False
    if end_row and not str(end_row).isalnum():
        valid_input = False
    if row_group_cols and len(row_group_cols) > 0:
        for i in row_group_cols:
            if not str(i['field']).isalnum():
                valid_input = False
                break
    if valid_input and value_cols and len(value_cols) > 0:
        for i in value_cols:
            if not str(i['aggFunc']).isalnum() or not str(i['id']).isalnum():
                valid_input = False
                break
    if valid_input and group_keys and len(group_keys) > 0:
        for i in group_keys:
            if not str(i).isalnum():
                valid_input = False
                break
    if valid_input and filter_model and len(filter_model) > 0:
        for key, value in filter_model.items():
            if not str(key).isalnum():
                valid_input = False
                break
            for val in value["values"]:
                if not str(val).isalnum():
                    valid_input = False
                    break
    if valid_input and sort_model and len(sort_model) > 0:
        for i in sort_model:
            if not str(i['sort']).isalnum() or not str(i['colId']).isalnum():
                valid_input = False
                break
    if not valid_input:
        return HttpResponse(json.dumps({}))


def flatten_array(array_of_array):
    flatlist = []
    for array in array_of_array:
        for ele in array:
            flatlist.append(ele)
    return flatlist


def execute_sql_query(sql):
    cursor = connection.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    x = cursor.description

    results_list = []
    for r in results:
        i = 0
        d = {}
        while i < len(x):
            key = str(x[i][0]).replace("_id", "")
            d[key] = r[i]
            i = i + 1
        results_list.append(d)
    return results_list


def handle_sql(sql, encrypt_key, key_replace={}):
    cursor = connection.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    x = cursor.description

    results_list = []
    for r in results:
        i = 0
        d = {}
        while i < len(x):
            key = str(x[i][0])
            if key == "id":
                d[key] = hash_value(r[i], encrypt_key)
            elif key in key_replace:
                d[key] = hash_value(r[i], key_replace[key])
            else:
                d[key] = r[i]
            i = i + 1
        results_list.append(d)

    return {
        "results": results_list,
        "lastRow": len(results_list),
    }
