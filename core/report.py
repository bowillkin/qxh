#coding=utf-8
from collections import defaultdict,OrderedDict
from datetime import datetime,timedelta

from extensions import db

from flask.ext.login import current_user

from flask import render_template,Blueprint,request
from utils.decorator import admin_required

from settings.constants import *
from .models import Order,Operator,Fuwu2,Fuwu,Jiexian,Waihu,Weihu,QXHKHDJ,User,QXHDM_Orderyf,User_Assign_Log
report = Blueprint('report',__name__,url_prefix='/report')

@report.route('/sale')
@admin_required
def sale_report():
    return render_template('report/sale_report.html')

@report.route('/sale/ddxsmxtj')
@admin_required
def sale_report_by_ddxsmxtj():
    _conditions = ['`order`.status<>103','`order`.status>1','`order`.status<200']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`created_by`=%d'%int(op_id))

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.`express_id`=%d'%int(express_id))


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`created`<="%s"'%_end_date)

    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin)    

    if not _start_date and not _end_date:
        period = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.`created`>="%s 00:00:00"'%period)
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
`order`.team,
operator.nickname,
`order`.username,
`order`.order_id,
`user`.origin,
`order_items`.item_info,
`order`.item_fee-`order`.discount_fee as `fee`,
`order`.discount_fee,
`order`.express_id,
`order`.express_number,
`order`.`created`
 FROM `order`
JOIN operator ON `order`.created_by=`operator`.id
JOIN `user` ON `user`.user_id=`order`.user_id
JOIN (SELECT `order_item`.`order_id` as oid,GROUP_CONCAT(CONCAT(`order_item`.name,'*',`order_item`.quantity) SEPARATOR '\n') as item_info FROM `order_item` GROUP BY `order_item`.`order_id`) AS order_items ON `order`.order_id=`order_items`.oid
WHERE %s ORDER BY `order`.team,`order`.`created`
    '''%' AND '.join(_conditions)
    _data = db.session.execute(_sql)
    _rows = []
    total_fee = 0
    for team,op_name,username,order_id,origin,item_info,fee,discount_fee,express_id,express_number,created in _data:
        total_fee += fee
        _rows.append({'depart':DEPARTMENTS[team[0]] if team else '',
                       'team':TEAMS[team] if team and len(team)==2 else '',
                       'op_name':op_name,
                       'username':username,
                       'origin':origin,
                       'order_id':order_id,
                       'items':item_info,
                       'fee':fee,
                       'discount_fee':discount_fee,
                       'express_name':EXPRESS_CONFIG[express_id]['name'] if express_id else '',
                       'express_number':express_number if express_number else '',
                       'created':created
                       })
    _op_sql = '''SELECT id,nickname FROM `operator` WHERE role_id=101'''
    _ops = db.session.execute(_op_sql)
    return render_template('report/sale_report_by_ddxsmxtj.html',rows=_rows,ops=_ops,total_fee=total_fee,period=period)


@report.route('/sale/arrival_detail')
@admin_required
def sale_report_by_arrival_detail():
    period = ''
    _conditions = ['`arrival_time` IS NOT NULL']#'`order`.status IN (6,60,100)',

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`created_by`=%d'%int(op_id))

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.`express_id`=%d'%int(express_id))

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`arrival_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`arrival_time`<="%s"'%_end_date)

    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin)  

    if not _start_date and not _end_date:
        period = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`arrival_time`>="%s 00:00:00"'%period)
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _itm_sql = '''SELECT operator.id,operator.nickname,`order`.team,`order`.username,`order`.order_id,`order_items`.item_info,`order`.item_fee-`order`.discount_fee,`order`.discount_fee,`order`.express_id,`order`.express_number,`arrival_time`,`user`.origin,`user`.m1,`user`.m2,`user`.m3 FROM `order` JOIN `operator` ON `order`.created_by=`operator`.id
 JOIN `user` ON `order`.user_id=`user`.user_id
JOIN (SELECT `order_item`.`order_id` as oid,GROUP_CONCAT(CONCAT(`order_item`.name,'*',`order_item`.quantity) SEPARATOR '\n') as item_info FROM `order_item` GROUP BY `order_item`.`order_id`) AS order_items ON `order`.order_id=`order_items`.oid
WHERE %s
ORDER BY `arrival_time`'''%' AND '.join(_conditions)
    rows = db.session.execute(_itm_sql)
    _op_sql = '''SELECT id,nickname FROM `operator` WHERE role_id=101'''
    _ops = db.session.execute(_op_sql)
    _rows = []
    total_fee = 0
    for data in rows:
        _rows.append(data)
        total_fee += data[6]

    return render_template('report/sale_report_by_arrival_detail.html',rows=_rows,ops=_ops,total_fee=total_fee,period=period)


@report.route('/sale/arrival_total')
@admin_required
def sale_report_by_arrival_total():
    period = ''
    _conditions = ['`arrival_time` IS NOT NULL']#'`order`.status IN (6,60,100)',
    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`created`<="%s"'%_s_end_date)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`arrival_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`arrival_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        period = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`arrival_time`>="%s 00:00:00"'%period)
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql2 = '''SELECT SUBSTRING(`order`.team,1,1) AS `t`,DATE(`order`.arrival_time) AS dt,COUNT(distinct order_id),SUM(`order`.item_fee-`order`.discount_fee) FROM `order` WHERE `order`.team<>'' AND %s
GROUP BY t,dt'''%' AND '.join(_conditions)
    col_rows = db.session.execute(_sql2)

    details = defaultdict(list)
    fee_totals = defaultdict(int)
    num_totals = defaultdict(int)
    for team,dt,orders,fee in col_rows:
        fee_totals[team]+= fee
        num_totals[team]+= orders
        details[team].append((dt,orders,fee))

    rows = []
    for team,detail in details.iteritems():
        orders = num_totals[team]
        fee = fee_totals[team]
        rows.append({'team':team,'fee':fee,'orders':orders,'avg_fee':fee/orders if orders>0 else 0,
                      'detail':detail,'n':len(detail)+1})
    return render_template('report/sale_report_by_arrival_total.html',rows=rows,period=period)


@report.route('/sale/return_detail')
@admin_required
def sale_report_by_return_detail():
    period = ''
    _conditions = ['`order`.status IN (102,104)','`end_time` IS NOT NULL']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`order`.`created_by`=%d'%int(op_id))

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.`express_id`=%d'%int(express_id))

    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin) 


    is_arrival = request.args.get('is_arrival',0)
    if is_arrival:
        is_arrival = int(is_arrival)
        if is_arrival == 1:
            _conditions.append('`order`.`arrival_time` is not null')
        elif is_arrival == 2:
            _conditions.append('`order`.`arrival_time` is null')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`created`<="%s"'%_s_end_date)


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`end_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`end_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        period = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`end_time`>="%s 00:00:00"'%period)
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _itm_sql = '''SELECT operator.id,operator.nickname,`order`.team,`order`.username,`user`.origin,`order`.order_id,`order_items`.item_info,`order`.item_fee-`order`.discount_fee,`order`.discount_fee,`order`.express_id,`order`.express_number,`end_time` FROM `order` 
                JOIN `operator` ON `order`.created_by=`operator`.id
                JOIN `user` ON `user`.user_id=`order`.user_id
                JOIN (SELECT `order_item`.`order_id` as oid,GROUP_CONCAT(CONCAT(`order_item`.name,'*',`order_item`.quantity) SEPARATOR '\n') as item_info FROM `order_item` 
                        GROUP BY `order_item`.`order_id`) AS order_items ON `order`.order_id=`order_items`.oid
                WHERE %s
                ORDER BY `end_time`'''%' AND '.join(_conditions)
    rows = db.session.execute(_itm_sql)

    _op_sql = '''SELECT id,nickname FROM `operator` WHERE role_id=101'''
    _ops = db.session.execute(_op_sql)
    _rows = []
    total_fee = 0
    for data in rows:
        _rows.append(data)
        total_fee += data[7]

    return render_template('report/sale_report_by_return_detail.html',rows=_rows,ops=_ops,total_fee=total_fee,period=period)


@report.route('/sale/return_total')
@admin_required
def sale_report_by_return_total():
    period = ''
    _conditions = ['`order`.status IN (102,104)','`end_time` IS NOT NULL']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`created`<="%s"'%_s_end_date)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`end_time`>="%s"'%_start_date)

    is_arrival = request.args.get('is_arrival',0)
    if is_arrival:
        is_arrival = int(is_arrival)
        if is_arrival == 1:
            _conditions.append('`order`.`arrival_time` is not null')
        elif is_arrival == 2:
            _conditions.append('`order`.`arrival_time` is null')

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`end_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        period = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`end_time`>="%s 00:00:00"'%period)
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql2 = '''SELECT SUBSTRING(team,1,1) AS `t`,DATE(`order`.end_time) AS dt,COUNT(distinct order_id),SUM(`order`.item_fee-`order`.discount_fee) FROM `order` WHERE `order`.team<>'' AND %s
GROUP BY t,dt'''%' AND '.join(_conditions)
    col_rows = db.session.execute(_sql2)

    details = defaultdict(list)
    fee_totals = defaultdict(int)
    num_totals = defaultdict(int)
    for team,dt,orders,fee in col_rows:
        fee_totals[team]+= fee
        num_totals[team]+= orders
        details[team].append((dt,orders,fee))

    rows = []
    for team,detail in details.iteritems():
        orders = num_totals[team]
        fee = fee_totals[team]
        rows.append({'team':team,'fee':fee,'orders':orders,'avg_fee':fee/orders if orders>0 else 0,
                     'detail':detail,'n':len(detail)+1})
    return render_template('report/sale_report_by_return_total.html',rows=rows,period=period)


@report.route('/sale/ygxs')
@admin_required
def sale_report_by_ygxs():
    period = ''
    _conditions = ['status NOT IN (1,103)','status<200']#['status IN (2,3,40,4,5,6,60,100)']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order_team` LIKE "'+current_user.team+'%"')

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _conditions.append('`order_date`="%s"'%datetime.now().strftime('%y%m%d'))
        period = datetime.now().strftime('%Y-%m-%d')
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _itm_sql = '''SELECT
                    operator_id,
                    item_name,
                    price,
                    SUM(quantity),
                    SUM(fee)
                FROM
                    `operator_order_items`
                WHERE
                    %s
                GROUP BY
                    operator_id,
                    item_name,
                    price'''%' AND '.join(_conditions)
    op_items = db.session.execute(_itm_sql)

    _op_items = defaultdict(list)
    for op_id,item_name,price,quantity,fee in op_items:
        _op_items[op_id].append((item_name,price,quantity,fee))

    # _count_sql = '''SELECT order_team,operator_id,nickname,count(DISTINCT order_id),SUM(fee) from operator_order_items WHERE %s GROUP BY order_team,operator_id,nickname ORDER BY order_team'''%' AND '.join(_conditions)
    _count_sql = '''SELECT order_team,operator_id,nickname,count(DISTINCT order_id),SUM(price*quantity) as fee from operator_order_items WHERE %s GROUP BY order_team,operator_id,nickname ORDER BY order_team'''%' AND '.join(_conditions)
    print '-------'
    rows=[]
    op_counts = db.session.execute(_count_sql)
    total_orders = 0
    total_fee = 0
    for team,op_id,nickname,order_nums,fee in op_counts:
        total_orders += order_nums
        total_fee += fee
        _items = _op_items[op_id]
        rows.append({'team':team,'op_id':op_id,'nickname':nickname,'order_nums':order_nums,'total_fee':fee,'items':_items,'n':len(_items)+1})
    return render_template('report/sale_report_by_ygxs.html',rows=rows,period=period,total_orders=total_orders,total_fee=total_fee)


@report.route('/sale/ygdhtj')
@admin_required
def sale_report_by_ygdhtj():
    period = ''
    _conditions = ['`arrival_time` IS NOT NULL']#'status IN (6,60,100)'#['status IN (2,3,40,4,5,6,60,100)']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order_team` LIKE "'+current_user.team+'%"')


    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`created`<="%s"'%_s_end_date)


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`arrival_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`arrival_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        period = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`arrival_time`>="%s 00:00:00"'%period)
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`operator_id`=%d'%int(op_id))

    _itm_sql = '''SELECT
                    operator_id,
                    order_team,
                    item_name,
                    price,
                    SUM(quantity),
                    SUM(price*quantity)
                FROM
                    `operator_order_items`
                WHERE
                    %s
                GROUP BY
                    operator_id,
                    order_team,
                    item_name,
                    price'''%' AND '.join(_conditions)
    #return _itm_sql
    op_items = db.session.execute(_itm_sql)

    _op_items = defaultdict(list)
    for op_id,team,item_name,price,quantity,fee in op_items:
        _op_items['%s-%s'%(op_id,team)].append((item_name,price,quantity,fee))

    # _count_sql = '''SELECT order_team,operator_id,nickname,count(DISTINCT order_id),SUM(fee) from operator_order_items WHERE %s GROUP BY order_team,operator_id,nickname ORDER BY order_team'''%' AND '.join(_conditions)
    _count_sql = '''SELECT order_team,operator_id,nickname,count(DISTINCT order_id),SUM(price*quantity) from operator_order_items WHERE %s GROUP BY order_team,operator_id,nickname ORDER BY order_team'''%' AND '.join(_conditions)

    _op_sql = '''SELECT id,nickname FROM `operator` WHERE role_id=101'''
    _ops = db.session.execute(_op_sql)

    rows=[]
    op_counts = db.session.execute(_count_sql)
    total_orders = 0
    total_fee = 0
    for team,op_id,nickname,order_nums,fee in op_counts:
        total_orders += order_nums
        total_fee += fee
        _items = _op_items['%s-%s'%(op_id,team)]
        rows.append({'team':team,'op_id':op_id,'nickname':nickname,'order_nums':order_nums,'total_fee':fee,'items':_items,'n':len(_items)+1})
        # _fee = sum(map(lambda i:i[3],_items))
        # if _fee<>fee:
        #     print nickname,_fee,fee
    return render_template('report/sale_report_by_ygdhtj.html',rows=rows,ops=_ops,period=period,total_orders=total_orders,total_fee=total_fee)


@report.route('/sale/staff')
@admin_required
def sale_report_by_staff():
    period = ''
    _conditions = ['`order`.status NOT IN (1,103)','`order`.status<200']#['`order`.status IN (2,3,40,4,5,6,60,100)']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _conditions.append('`order`.`date`="%s"'%datetime.now().strftime('%y%m%d'))
        period = datetime.now().strftime('%Y-%m-%d')
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
`operator`.id,`operator`.nickname,`order`.`team`,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums`
FROM `order` LEFT JOIN `operator` ON `order`.created_by = `operator`.id
WHERE %s
GROUP BY `operator`.id,`operator`.nickname,`order`.`team` ORDER BY `order`.`team`'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[3]
        total_fee += r[4]

    _sql2 = '''SELECT `order`.team,operator.id,operator.nickname,DATE(`order`.created) AS dt,COUNT(distinct order_id),SUM(`order`.item_fee-`order`.discount_fee) FROM `order` JOIN `operator` ON `order`.created_by=`operator`.id
WHERE %s
GROUP BY `order`.team,operator.id,operator.nickname,dt ORDER BY `order`.team,dt'''%' AND '.join(_conditions)
    col_rows = db.session.execute(_sql2)

    details = defaultdict(list)
    fee_totals = defaultdict(int)
    num_totals = defaultdict(int)
    op_infos = {}
    for team,op_id,op_name,dt,orders,fee in col_rows:
        fee_totals[op_id]+= fee
        num_totals[op_id]+= orders
        details[op_id].append((dt,orders,fee))
        if not op_infos.has_key(op_id):
            op_infos[op_id] = (team,op_name)


    rows2 = []
    for op_id,data in op_infos.iteritems():
        orders = num_totals[op_id]
        fee = fee_totals[op_id]
        team,op_name = data
        detail = details[op_id]
        rows2.append({'team':team,'id':op_id,'op_name':op_name,'fee':fee,'orders':orders,'avg_fee':fee/orders if orders>0 else 0,
                      'detail':detail,'n':len(detail)+1})

    rows2 = sorted(rows2,key=lambda d:d['team'])
    return render_template('report/sale_report_by_staff.html',rows=_rows,rows2=rows2,period=period,total_orders=total_orders,total_fee=total_fee)

@report.route('/')
@admin_required
def sale_report_by_team():
    period = ''
    _conditions = ['`order`.status NOT IN (1,103)','`order`.status<200']#['`order`.status IN (2,3,40,4,5,6,60,100)']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _conditions.append('`order`.`date`="%s"'%datetime.now().strftime('%y%m%d'))
        period = datetime.now().strftime('%Y-%m-%d')
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
`order`.team,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
 SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums` FROM `order` LEFT JOIN `operator` ON `order`.created_by = `operator`.id
WHERE %s
GROUP BY `order`.team'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[1]
        total_fee += r[2]


    _sql2 = '''SELECT SUBSTRING(`order`.team,1,1) AS `t`,DATE(`order`.created) AS dt,SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 0 ELSE 1 END) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) FROM `order` WHERE `order`.team<>'' AND %s
GROUP BY t,dt'''%' AND '.join(_conditions)
    col_rows = db.session.execute(_sql2)

    details = defaultdict(list)
    fee_totals = defaultdict(int)
    num_totals = defaultdict(int)
    for team,dt,orders,fee in col_rows:
        orders = int(orders)
        fee_totals[team]+= fee
        num_totals[team]+= orders
        details[team].append((dt,orders,fee))

    rows2 = []
    for team,detail in details.iteritems():
        orders = num_totals[team]
        fee = fee_totals[team]
        rows2.append({'team':team,'fee':fee,'orders':orders,'avg_fee':fee/orders if orders>0 else 0,
                      'detail':detail,'n':len(detail)+1})
    return render_template('report/sale_report_by_team.html',rows=_rows,rows2=rows2,period=period,total_orders=total_orders,total_fee=total_fee)

@report.route('/sale/item')
@admin_required
def sale_report_by_item():
    period = ''
    _conditions = ['`order`.status NOT IN (1,103)','`order`.status<200']#['`order`.status IN (2,3,40,4,5,6,60,100)']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')
    else:
        _depart = request.args.get('depart','')
        if _depart:
            _conditions.append('`order`.team LIKE "%s%%"'%_depart)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _conditions.append('`order`.`date`="%s"'%datetime.now().strftime('%y%m%d'))
        period = datetime.now().strftime('%Y-%m-%d')
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    # _sql = '''SELECT `sku_item`.`category_id`,`order_item`.`sku_id`,`order_item`.name,SUM(`order_item`.quantity),SUM(`order_item`.fee)
    # FROM `order_item`
    # JOIN (SELECT `order_id` FROM `order` WHERE %s) AS `orders` ON `order_item`.order_id=`orders`.order_id
    # LEFT JOIN (SELECT `item`.`category_id`,`sku`.id AS `sku_id` FROM `item` JOIN `sku` ON `item`.id=`sku`.item_id) AS `sku_item` ON `sku_item`.sku_id=`order_item`.sku_id
    # GROUP BY `sku_item`.`category_id`,`order_item`.`sku_id`,`order_item`.name'''%' AND '.join(_conditions)

    _sql = '''SELECT `sku_item`.`category_id`,`order_item`.`sku_id`,`order_item`.name,SUM(`order_item`.quantity),SUM(`order_item`.quantity*`order_item`.price)
    FROM `order_item`
    JOIN (SELECT `order_id` FROM `order` WHERE %s) AS `orders` ON `order_item`.order_id=`orders`.order_id
    LEFT JOIN (SELECT `item`.`category_id`,`sku`.id AS `sku_id` FROM `item` JOIN `sku` ON `item`.id=`sku`.item_id) AS `sku_item` ON `sku_item`.sku_id=`order_item`.sku_id
    GROUP BY `sku_item`.`category_id`,`order_item`.`sku_id`,`order_item`.name'''%' AND '.join(_conditions)
    print _sql
    rows = db.session.execute(_sql)
    detail = defaultdict(list)
    for category_id,sku_id,item_name,quantity,fee in rows:
        detail[category_id].append({'sku_id':sku_id,'item_name':item_name,'quantity':quantity,'fee':fee})

    data = []
    for c_id,items in detail.iteritems():
        data.append({'category_id':c_id,'category_name':ITEM_CATEGORYS[c_id],
                     'items':items,'quantity':sum(map(lambda s:s['quantity'],items)),
                     'fee':sum(map(lambda s:s['fee'],items)),
                     'num':len(items)})
    return render_template('report/sale_report_by_item.html',data=data,period=period)


@report.route('/financial')
@admin_required
def financial_report():
    return render_template('report/financial_report.html')



@report.route('/financial/sale')
@admin_required
def financial_report_by_sale():
    #_conditions = ['`order`.delivery_time IS NOT NULL','`order`.order_type<100']
    _conditions = ['`order`.delivery_time IS NOT NULL']

    order_type = request.args.get('order_type',0)
    if order_type:
        _conditions.append('`order`.order_type=%s'%order_type)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.delivery_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.delivery_time<="%s"'%_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.delivery_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql2 = '''SELECT
                `order`.express_id,
                COUNT(DISTINCT `order`.order_id),SUM(`order`.item_fee-`order`.discount_fee) as sumfee FROM `order`
                WHERE
                %s
                GROUP BY `order`.express_id'''%' AND '.join(_conditions)
    orders = db.session.execute(_sql2)
    #print _sql2
    totalree = []#所有订单总额
    totalorders = []#所有订单数

    item_type = request.args.get('item_type','')
    if item_type:
        item_type = int(item_type)
        if item_type == 1:_conditions.append('`order_item`.fee>0')
        elif item_type == 2:_conditions.append('`order_item`.fee=0')

    _sql = '''SELECT
                `order`.express_id,
                `order_item`.name,
                `order_item`.price,
                SUM(`order_item`.quantity),
                SUM(`order_item`.fee)
            FROM `order_item`
            JOIN `order` ON `order_item`.order_id=`order`.order_id
            WHERE
            %s
            GROUP BY `order`.express_id,`order_item`.name,`order_item`.price ORDER BY `order`.express_id'''%' AND '.join(_conditions)
    print _sql
    data = db.session.execute(_sql)
    return render_template('report/financial_report_by_fh.html',totalorders=totalorders,totalree=totalree,data=data,orders=orders,period=period)


@report.route('/financial/return')
@admin_required
def financial_report_by_return():
    # _conditions = ['`order`.status IN (102,104)','`order`.order_type<100']
    _conditions = ['`order`.status>100','`order`.status<200','`order`.order_type<100','`order`.delivery_time IS NOT NULL','`order`.arrival_time IS NULL']

    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`created_by`=%d'%int(op_id))

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.`express_id`=%d'%int(express_id))

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    order_type = request.args.get('order_type',0)
    if order_type:
        _conditions.append('`order`.order_type=%s'%order_type)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.end_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.end_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.end_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql2 = '''SELECT
                `order`.express_id,
                COUNT(DISTINCT `order`.order_id),SUM(`order`.item_fee) as sumfee FROM `order`
                WHERE
                %s
                GROUP BY `order`.express_id'''%' AND '.join(_conditions)
    orders = db.session.execute(_sql2)
    totalree = []#所有订单总额
    totalorders = []#所有订单数


    item_type = request.args.get('item_type','')
    if item_type:
        item_type = int(item_type)
        if item_type == 1:_conditions.append('`order_item`.fee>0')
        elif item_type == 2:_conditions.append('`order_item`.fee=0')

    _sql = '''SELECT
                `order`.express_id,
                `order_item`.name,
                `order_item`.price,
                SUM(`order_item`.in_quantity),
                SUM(`order_item`.fee)
            FROM `order_item`
            JOIN `order` ON `order_item`.order_id=`order`.order_id
            WHERE
            %s
            GROUP BY `order`.express_id,`order_item`.name,`order_item`.price ORDER BY `order`.express_id'''%' AND '.join(_conditions)
    data = db.session.execute(_sql)
    _op_sql = '''SELECT id,nickname FROM `operator` WHERE role_id=101'''
    _ops = db.session.execute(_op_sql)

    return render_template('report/financial_report_by_fh.html',totalorders=totalorders,ops=_ops,totalree=totalree,data=data,orders=orders,period=period)


@report.route('/financial/dzbb')
@admin_required
def financial_report_by_dzbb():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order_log`.`operate_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order_log`.`operate_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order_log`.`operate_time`>="%s 00:00:00"'%_today)
        _conditions.append('`order_log`.`operate_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `tmp_order`.express_id,`tmp_order`.order_id,order_item.sku_id,order_item.name,SUM(`order_item`.quantity),SUM(`order_item`.fee) FROM `order_item`
JOIN (SELECT `order`.order_id,`order`.express_id FROM `order` JOIN `order_log` ON %s) AS `tmp_order` ON `tmp_order`.`order_id`=`order_item`.order_id
GROUP BY `tmp_order`.express_id,order_item.sku_id,order_item.name ORDER BY `tmp_order`.express_id'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = []
    for express_id,order_id,sku_id,item_name,quantity,fee in rows:
        data.append({'express_name':EXPRESS_CONFIG[express_id]['name'],
                     'item_name':item_name,
                     'quantity':quantity,
                     'fee':fee})
    return render_template('report/financial_report_by_dzbb.html',data=data,period=period)


@report.route('/financial/paidan')
@admin_required
def financial_report_by_paidan():
    period = ''
    #_conditions = ['`order`.order_type<100']
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.delivery_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.delivery_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.delivery_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)
        
    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin)
        
    #_conditions = ["`order`.created>'2015-03-01'"]
    #_conditions.append("`order`.created<'2015-10-01'")
    #_conditions.append("`order`.user_id in (SELECT user_id from `user_phone` WHERE phone in (82124201))")
    
    _sql = '''SELECT `order`.order_type,`operator`.nickname,`order`.team,`order`.delivery_time,`order`.order_id,`express_id`,`express_number`,`ship_to`,`user`.origin,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.delivery_time IS NOT NULL
JOIN `address` ON `order`.shipping_address_id=`address`.id
JOIN `operator` ON `operator`.id=`order`.created_by
JOIN `user` ON `user`.user_id=`address`.user_id
WHERE %s
ORDER BY `order`.delivery_time'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for order_type,op_name,team,delivery_time,order_id,express_id,express_number,ship_to,origin,province,city,district,street1,fee,item_name,price,quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                            'department':DEPARTMENTS.get(team[0],'') if team else '',
                            'team':TEAMS.get(team,'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'ordertype':ORDER_TYPES[order_type],
                              'fee':fee,
                              'id':order_id,
                              'date':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'origin':origin,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1
                              }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_paidan.html',data=_data,period=period)


@report.route('/financial/paidan/tuihuo')
@admin_required
def financial_report_by_paidan_tuihuo():
    period = ''
    _conditions = ['`order`.status>100','`order`.order_type<100','`order`.status<200']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.end_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.end_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.end_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)
    
    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin)
    

    _sql = '''SELECT `operator`.nickname,`order`.`team`,`order`.delivery_time,`order`.end_time,`order`.order_id,`express_id`,`express_number`,`ship_to`,`user`.origin,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.in_quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.delivery_time IS NOT NULL AND `order`.arrival_time IS NULL
JOIN `address` ON `order`.shipping_address_id=`address`.id
JOIN `operator` ON `operator`.id=`order`.created_by
JOIN `user` ON `user`.user_id=`address`.user_id
WHERE %s
ORDER BY `order`.end_time'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for op_name,team,delivery_time,end_time,order_id,express_id,express_number,ship_to,origin,province,city,district,street1,fee,item_name,price,quantity,in_quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                            'department':DEPARTMENTS.get(team[0],'') if team else '',
                            'team':TEAMS.get(team,'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':end_time.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'origin':origin,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1
            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'in':in_quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_paidan_tuihuo.html',data=_data,period=period)



@report.route('/financial/qianshou')
@admin_required
def financial_report_by_qianshou():
    period = ''
    #_conditions = ['`order`.order_type<100']
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.arrival_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.arrival_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.arrival_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    #_conditions.append('`user`.remark="527微信抽奖"')
    #_conditions.append('`order`.created>"2015-09-01" and `order`.created<"2015-11-01"')
    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)
    
    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin)
    

    _sql = '''SELECT `operator`.nickname,`order`.delivery_time,`order`.team,`order`.arrival_time,`order`.order_id,`express_id`,`express_number`,`ship_to`,`user`.origin,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.fee,`user`.m1,`user`.m2,`user`.m3 FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.arrival_time IS NOT NULL
 JOIN `user` ON `order`.user_id=`user`.user_id
JOIN `operator` ON `operator`.id=`order`.created_by
JOIN `address` ON `order`.shipping_address_id=`address`.id
WHERE %s and `user`.user_id=`address`.user_id
ORDER BY `order`.arrival_time'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for op_name,delivery_time,team,arrival_time,order_id,express_id,express_number,ship_to,origin,province,city,district,street1,fee,item_name,price,quantity,item_fee,m1,m2,m3 in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                            'department':DEPARTMENTS.get(team[0],'') if team else '',
                            'team':TEAMS.get(team,'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':arrival_time.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'origin':origin,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1,
                              'm1':m1,
                              'm2':m2,
                              'm3':m3
            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_qianshou.html',data=_data,period=period)


@report.route('/financial/qianshou/tuihuo')
@admin_required
def financial_report_by_qianshou_tuihuo():
    period = ''
    _conditions = ['`order`.status>100','`order`.status<200','`order`.express_number IS NOT NULL','`order`.order_type<100']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.end_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.end_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.end_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `operator`.nickname,`order`.delivery_time,`order`.team,`order`.end_time,`order`.order_id,`express_id`,`express_number`,`ship_to`,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.in_quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.arrival_time IS NOT NULL
JOIN `operator` ON `operator`.id=`order`.created_by
JOIN `address` ON `order`.shipping_address_id=`address`.id
WHERE %s
ORDER BY `order`.end_time'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for op_name,delivery_time,team,end_time,order_id,express_id,express_number,ship_to,province,city,district,street1,fee,item_name,price,quantity,in_quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                            'department':DEPARTMENTS.get(team[0],'') if team else '',
                            'team':TEAMS.get(team,'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':end_time.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1
            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'in_num':in_quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_qianshou_tuihuo.html',data=_data,period=period)


############################################################################################

@report.route('/logistics')
@admin_required
def logistics_report():
    return render_template('report/logistics_report.html')


@report.route('/logistics/wlfhhz')
@admin_required
def logistics_report_by_wlfhhz():
    period = ''
    _conditions = ['`order`.delivery_time IS NOT NULL']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.delivery_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.delivery_time<="%s"'%_end_date)

    store_id = request.args.get('store_id','')
    if store_id:
        _conditions.append('`order`.store_id=%s'%int(store_id))

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.delivery_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `order`.express_id,`order_item`.sku_id,`order_item`.name,SUM(`order_item`.quantity),SUM(`order_item`.fee) FROM
`order_item`
JOIN `order` ON order_item.order_id=`order`.order_id WHERE %s GROUP BY `order`.express_id,`order_item`.sku_id,`order_item`.name'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    data = []
    for express_id,sku_id,name,qty,fee in rows:
        data.append({'ename':EXPRESS_CONFIG[int(express_id)]['name'],'name':name,'qty':qty,'fee':fee})
    return render_template('report/logistics_report_by_wlfhhz.html',data=data,period=period)



@report.route('/logistics/day/delivery')
@admin_required
def logistics_report_by_day_delivery():
    period = ''
    _conditions = ['`order`.delivery_time IS NOT NULL']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.delivery_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.delivery_time<="%s"'%_end_date)

    store_id = request.args.get('store_id','')
    #增加库房的选择物流
    if current_user.role_id in KF_ROOLEIDS:
        store_id=current_user.store_id
    if store_id:
        _conditions.append('`order`.store_id=%s'%int(store_id))
    
    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.delivery_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `order`.order_id,`order`.store_id,`order`.express_id,`order`.express_number,`order`.`payment_type`,`order`.item_fee-`order`.discount_fee,`order`.`delivery_time`,`order_item`.name,`order_item`.quantity,`order_item`.fee FROM
`order_item`
JOIN `order` ON order_item.order_id=`order`.order_id WHERE %s'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for order_id,store_id,express_id,express_number,payment_type,fee,dt,item_name,quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'store_name':STORES[store_id],
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'payment':ORDER_PAYMENTS[payment_type],
                              'date':dt.strftime("%Y-%m-%d"),
                              'items':[]}
        data[order_id]['items'].append({'name':item_name,'num':quantity,'fee':item_fee})

    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/logistics_report_by_day_deliver.html',data=_data,period=period)


from utils.tools import c_dict

@report.route('/logistics/io')
@admin_required
def logistics_report_by_io():
    period = ''
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`stock_inventory`.`date`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`stock_inventory`.`date`<="%s"'%_end_date)

    store_id = request.args.get('store_id','')
    #增加库房的选择物流
    if current_user.role_id in KF_ROOLEIDS:
        store_id=current_user.store_id    
    if store_id:
        _conditions.append('`stock_inventory`.store_id=%s'%int(store_id))

    if not _start_date and not _end_date:
        _yestoday = (datetime.now()+timedelta(days=-1)).strftime('%Y-%m-%d')
        _conditions.append('`stock_inventory`.`date`>="%s"'%_yestoday)
        period = _yestoday
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT `sku_id`,`store_id`,`sku`.`name`,`ins`,`in_quantity`,`outs`,`out_quantity`,`stock_inventory`.`quantity`,`date`
     FROM `stock_inventory` JOIN `sku` ON `stock_inventory`.`sku_id`=`sku`.`id` WHERE %s ORDER BY `store_id`,`sku_id`,`date`
    '''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = []
    for sku_id,store_id,name,ins,in_quantity,outs,out_quantity,quantity,date in rows:
        _ins = defaultdict(int)
        _outs = defaultdict(int)
        if ins:_ins.update(eval('{%s}' % ins,c_dict))
        if outs:_outs.update(eval('{%s}' % outs,c_dict))
        data.append({'date':date,'store':STORES[store_id],'name':name,'in_quantity':in_quantity,'ins':_ins,'out_quantity':out_quantity,'outs':_outs,'quantity':quantity})
    return render_template('report/logistics_report_by_io.html',data=data,period=period)


@report.route('/logistics/loss')
@admin_required
def logistics_report_by_loss():
    period = ''
    _conditions = []#['loss.status=9']

    _channel = request.args.get('channel','')
    if _channel:
        _conditions.append('`loss`.`channel`>="%s"'%_channel)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`loss`.`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`loss`.`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`loss`.`created`>="%s 00:00:00"'%_today)
        _conditions.append('`loss`.`created`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT `sku`.id,`sku`.`name`,`loss`.degree,SUM(`loss`.quantity) FROM `loss` JOIN `sku` ON `loss`.sku_id=`sku`.id
WHERE %s
GROUP BY `sku`.id,`sku`.`name`,`loss`.degree'''%' AND '.join(_conditions)
    
    rows = db.session.execute(_sql)
    data = {}
    for sku_id,name,degree,quantity in rows:
        if not data.has_key(sku_id):
            data[sku_id] = {'sku_id':sku_id,'name':name,'total':0}
            for k in LOSS_DEGREES.keys():
                data[sku_id][str(k)] = 0
        data[sku_id][str(degree)] += quantity
        data[sku_id]['total'] += quantity
    return render_template('report/logistics_report_by_loss.html',data=data,period=period)

#add by john
@report.route('/financial/dzbbmx')
@admin_required
def financial_report_by_dzbbmx():
    period = ''
    #_conditions = ['`order`.order_type<100']
    _conditions = []
    _start_date = request.args.get('start_date','')
    #_conditions.append('`order`.status=60')
    if _start_date:
        _conditions.append('`order_log`.`operate_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order_log`.`operate_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order_log`.`operate_time`>="%s 00:00:00"'%_today)
        _conditions.append('`order_log`.`operate_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)
    
    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)
    
    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)
        
    user_origin = request.args.get('user_origin',0)
    if user_origin:
        _conditions.append('`user`.origin=%s'%user_origin)

    _sql = '''SELECT `operator`.nickname,`order`.delivery_time,`order`.arrival_time,`order`.team,`order_log`.operate_time,`order`.order_id,`express_id`,`express_number`,`ship_to`,`user`.origin,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id
JOIN `operator` ON `operator`.id=`order`.operator_id
JOIN `address` ON `order`.shipping_address_id=`address`.id
JOIN `order_log` ON `order_log`.to_status=60 and `order_log`.order_id=`order`.order_id
JOIN `user` ON `user`.user_id=`address`.user_id
WHERE %s
ORDER BY `order_log`.operate_time desc'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for op_name,delivery_time,arrival_time,team,operate_time,order_id,express_id,express_number,ship_to,origin,province,city,district,street1,fee,item_name,price,quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                            'department':DEPARTMENTS.get(team[0],'') if team else '',
                            'team':TEAMS.get(team,'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':operate_time.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'arrival_time':arrival_time,
                              'items':[],
                              'ship_to':ship_to,
                              'origin':origin,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1
            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_dzbbmx.html',data=_data,period=period)

#物流派单表统计
@report.route('/financia/paidan/tongji')
@admin_required
def financial_report_by_paidantongji():
    period = ''
    #_conditions = ['`order`.order_type<100']
    _conditions = []

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.delivery_time>="%s 00:00:00"'%_today)
        period = _today        
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
`order`.team,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
 SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums`,`order`.express_id FROM `order` LEFT JOIN `operator` ON `order`.created_by = `operator`.id
WHERE %s
GROUP BY `order`.team,`order`.express_id ORDER BY `order`.express_id,`order`.team'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[1]
        total_fee += r[2]
    return render_template('report/financial_report_by_paidantongji.html',rows=_rows,period=period,total_orders=total_orders,total_fee=total_fee)

#物流派单退货统计
@report.route('/financial/paidan/tuihuo/tongji')
@admin_required
def financial_report_by_paidantuihuotongji():
    _conditions = ['`order`.status>100','`order`.status<200','`order`.order_type<100']
    period = ''
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.end_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.end_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.end_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT
`order`.team,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
 SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums`,`order`.express_id FROM `order` LEFT JOIN `operator` ON `order`.created_by = `operator`.id
JOIN `address` ON `order`.shipping_address_id=`address`.id
WHERE %s  AND `order`.delivery_time IS NOT NULL AND `order`.arrival_time IS NULL
GROUP BY `order`.team,`order`.express_id ORDER BY `order`.express_id,`order`.team'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[1]
        total_fee += r[2]
    return render_template('report/financial_report_by_paidan_tuihuotongji.html',rows=_rows,period=period,total_orders=total_orders,total_fee=total_fee)

#物流签收表统计
@report.route('/financia/qianshou/tongji')
@admin_required
def financial_report_by_qianshoutongji():
    #_conditions = ['`order`.order_type<100']
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.arrival_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.arrival_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.arrival_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_s_end_date)

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)
    

    _sql = '''SELECT
`order`.team,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
 SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums`,`order`.express_id FROM `order` LEFT JOIN `operator` ON `order`.created_by = `operator`.id
JOIN `address` ON `order`.shipping_address_id=`address`.id
WHERE %s AND `order`.arrival_time IS NOT NULL
GROUP BY `order`.team,`order`.express_id ORDER BY `order`.express_id,`order`.team'''%' AND '.join(_conditions)
    #return _sql    
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[1]
        total_fee += r[2]
    return render_template('report/financial_report_by_qianshoutongji.html',rows=_rows,period=period,total_orders=total_orders,total_fee=total_fee)

#会员客户数量统计
@report.route('/sale/user_total')
@admin_required
def sale_report_by_user_total():
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user_statistics`.tjdate>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user_statistics`.tjdate<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user_statistics`.tjdate>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT * FROM user_statistics
 WHERE %s order by tjdate desc'''%' AND '.join(_conditions)
        
    
    #return _sql    
    rows = db.session.execute(_sql)
    total_new_users = 0
    total_giveup_users = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_new_users += r[1]
        total_giveup_users += r[2]
    return render_template('report/sale_report_by_user_total.html',rows=_rows,period=period,total_new_users=total_new_users,total_giveup_users=total_giveup_users)


#外呼统计
@report.route('/outbound/tongji')
@admin_required
def jiexian_tongji():
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`outbound`.created>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`outbound`.created<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`outbound`.created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql1 = '''SELECT COUNT(distinct outbound.user_id) user_ids FROM `outbound` 
join `user` on `user`.user_id = `outbound`.user_id
 WHERE %s'''%' AND '.join(_conditions)
    
    _sql2 = '''SELECT COUNT(distinct user_id) from `order` where user_id in (SELECT `outbound`.user_id FROM `outbound` 
         WHERE date(`order`.created)=date(`outbound`.created) and %s)'''%' AND '.join(_conditions)
    
    _sql3 = '''SELECT COUNT(distinct user_id) from `order` where user_id in (SELECT `outbound`.user_id FROM `outbound` 
         WHERE date(`order`.created)>date(`outbound`.created) and %s)'''%' AND '.join(_conditions)
    
    _sql4 = '''SELECT COUNT(distinct outbound.user_id) user_ids FROM `outbound` 
join `user` on `user`.user_id = `outbound`.user_id
         WHERE  `user`.order_num=0 and %s'''%' AND '.join(_conditions)
    
    _sql5 = '''SELECT group_concat(distinct user_id) from `order` where user_id in (SELECT `outbound`.user_id FROM `outbound` 
join `user` on `user`.user_id = `outbound`.user_id
         WHERE date(`order`.created)=date(`outbound`.created) and %s)'''%' AND '.join(_conditions)
        
    
    _sql6 = '''SELECT group_concat(distinct outbound.user_id) user_ids FROM `outbound` 
    join `user` on `user`.user_id = `outbound`.user_id
     WHERE %s'''%' AND '.join(_conditions)
    

    
    _sql = _sql1+' union all '+_sql2+' union all '+_sql3+' union all '+_sql4#+' union all '+_sql6
    #return _sql4
    rows = db.session.execute(_sql)
    return render_template('report/user_report_by_outbound.html',rows=rows,period=period)
#心力健统计
@report.route('/xlj/tongji')
@admin_required
def xlj_tongji():
    _conditions = ["`user`.origin=11"]
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.join_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.join_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.join_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql1 = '''SELECT COUNT(distinct user.user_id) user_ids FROM `user`
 WHERE %s'''%' AND '.join(_conditions)
    
    _sql2 = '''SELECT COUNT(distinct user.user_id) from `user` join `order` on user.user_id=`order`.user_id 
         WHERE user.user_id in (select a.user_id from (select count(*) as cc,user_id from `order` where is_xlj=1 and `order`.status>1 and `order`.status<200 group by user_id) a where a.cc=1) AND %s'''%' AND '.join(_conditions)
    
    
    _sql3 = '''SELECT COUNT(distinct user.user_id) from `user` join `order` on user.user_id=`order`.user_id 
         WHERE user.user_id in (select a.user_id from (select count(*) as cc,user_id from `order` where is_xlj=1 and `order`.status>1 and `order`.status<200 group by user_id) a where a.cc=2) AND %s'''%' AND '.join(_conditions)
    
    _sql4 = '''SELECT COUNT(distinct user.user_id) from `user` join `order` on user.user_id=`order`.user_id 
         WHERE user.user_id in (select a.user_id from (select count(*) as cc,user_id from `order` where is_xlj=1 and `order`.status>1 and `order`.status<200 group by user_id) a where a.cc=3) AND %s'''%' AND '.join(_conditions)
    
    
    _sql5 = '''SELECT COUNT(distinct user.user_id) from `user` join `order` on user.user_id=`order`.user_id 
         WHERE user.user_id in (select a.user_id from (select count(*) as cc,user_id from `order` where is_xlj=1 and `order`.status>1 and `order`.status<200 group by user_id) a where a.cc>3) AND %s'''%' AND '.join(_conditions)
    
    _sql6 = '''SELECT COUNT(distinct user.user_id) from `user` 
         WHERE user.user_id not in (select user_id from `order` where is_xlj=1 and `order`.status>1 and `order`.status<200 ) AND %s'''%' AND '.join(_conditions)
    
    
    
    
    _sql = _sql1+' union all '+_sql2+' union all '+_sql3+' union all '+_sql4+' union all '+_sql5+' union all '+_sql6
    #return _sql2
    rows = db.session.execute(_sql)
    return render_template('report/user_report_by_xlj.html',rows=rows,period=period)
#心力健销售统计
@report.route('/xlj/sale_tongji')
@admin_required
def xlj_sale_tongji():
    _conditions = []
    _m1 = request.args.get('m1','')
    if _m1:
        _conditions.append('`user`.m1="%s"'%_m1)
    _m2 = request.args.get('m2','')
    if _m2:
        _conditions.append('`user`.m2="%s"'%_m2)
    _m3 = request.args.get('m3','')
    if _m3:
        _conditions.append('`user`.m3="%s"'%_m3)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.created>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.created<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql1 = '''SELECT COUNT(distinct `order`.order_id) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=14 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)
    #return _sql1
    _sql2 = '''SELECT COUNT(distinct `order`.order_id) from `order` join order_log on order_log.order_id=`order`.order_id join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=14 AND `order`.status NOT IN (1,103) and `order`.status<200 AND order_log.to_status=6 AND %s'''%' AND '.join(_conditions)
    #return _sql2
    
    _sql3 = '''SELECT sum(`order`.item_fee-`order`.discount_fee) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)
    #return _sql3
    _sql4 = '''SELECT COUNT(distinct `order`.order_id) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)
    #return _sql4
    
    _sql5 = '''SELECT round(avg(`order`.item_fee-`order`.discount_fee),2) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)
    #return _sql5
    _sql6 = '''SELECT sum(`order`.item_fee-`order`.discount_fee) from `order` join order_log on order_log.order_id=`order`.order_id join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND order_log.to_status=6 AND %s'''%' AND '.join(_conditions)

    
    _sql7 = '''SELECT COUNT(distinct `order`.order_id) from `order` join order_log on order_log.order_id=`order`.order_id join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND order_log.to_status=6 AND %s'''%' AND '.join(_conditions)

    
    _sql8 = '''SELECT sum(`order`.item_fee-`order`.discount_fee) from `order` join order_log on order_log.order_id=`order`.order_id join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND order_log.to_status in (9,10) AND %s'''%' AND '.join(_conditions)

    
    _sql9 = '''SELECT COUNT(distinct `order`.order_id) from `order` join order_log on order_log.order_id=`order`.order_id join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=15 AND `order`.status NOT IN (1,103) and `order`.status<200 AND order_log.to_status in (9,10) AND %s'''%' AND '.join(_conditions)

    
    _sql10 = '''SELECT sum(`order`.item_fee-`order`.discount_fee) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=16 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)

    _sql11 = '''SELECT COUNT(distinct `order`.order_id) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=16 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)


    _sql12 = '''SELECT round(avg(`order`.item_fee-`order`.discount_fee),2) from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=16 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s'''%' AND '.join(_conditions)


    _sql = _sql1+' union all '+_sql2+' union all '+_sql3+' union all '+_sql4+' union all '+_sql5+' union all '+_sql6+' union all '+_sql7+' union all '+_sql8+' union all '+_sql9+' union all '+_sql10+' union all '+_sql11+' union all '+_sql12
    #return _sql
    rows = db.session.execute(_sql)
    return render_template('report/user_report_by_xlj_sale.html',rows=rows,period=period)
#心力健媒体进线情况表
@report.route('/xlj/mtjxqk')
@admin_required
def xlj_mtjxqk():
    _conditions = ["`user`.origin=11"]
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.join_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.join_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.join_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql1 = '''SELECT COUNT(distinct user.user_id),m1,m2 user_ids FROM `user`
 WHERE %s group by m1,m2 order by `user`.m1,`user`.m2'''%' AND '.join(_conditions)
    #return _sql1
    _sql2 = '''SELECT COUNT(distinct `order`.order_id),`user`.m1,`user`.m2 from `order` join `user` on user.user_id=`order`.user_id 
         WHERE `order`.order_type=14 AND `order`.status NOT IN (1,103) and `order`.status<200 AND %s group by `user`.m1,`user`.m2 order by `user`.m1,`user`.m2'''%' AND '.join(_conditions)

    
    totaljx = []#所有订单总额
    totalss = []#所有订单数
    
    #return _sql2
    rows = db.session.execute(_sql1)
    rows2 = db.session.execute(_sql2)
    return render_template('report/user_report_by_xljjxqkb.html',totaljx=totaljx,totalss=totalss,rows=rows,rows2=rows2,period=period)
#心力健销售情况表
@report.route('/xlj/xsqkb')
@admin_required
def xlj_xsqkb():
    _conditions = ["`user`.origin=11"]
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.join_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.join_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.join_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql1 = '''select `operator`.nickname,group_concat(`user`.phone,`user`.m1,`user`.m2),COUNT(distinct user.user_id) from user join `operator` on `user`.assign_operator_id=`operator`.id
 WHERE %s group by `user`.assign_operator_id order by `user`.assign_operator_id'''%' AND '.join(_conditions)
    db.session.execute('SET SESSION group_concat_max_len=10240')
    rows = db.session.execute(_sql1)
    return render_template('report/user_report_by_xsqkb.html',rows=rows,period=period)

#物流派单在途明细表
@report.route('/financial/paidan/zaitu')
@admin_required
def financial_report_by_paidan_zaitu():
    period = ''
    _conditions = ['`order`.status=5']
    
    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`created`<="%s"'%_s_end_date)

    if not _s_start_date and not _s_end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_s_start_date if _s_start_date else u'开始',_s_end_date if _s_end_date else u'现在')

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `operator`.nickname,`order`.`team`,`order`.delivery_time,`order`.created,`order`.order_id,`express_id`,`express_number`,`ship_to`,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.in_quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.delivery_time IS NOT NULL AND `order`.arrival_time IS NULL
JOIN `address` ON `order`.shipping_address_id=`address`.id
JOIN `operator` ON `operator`.id=`order`.created_by
WHERE %s
ORDER BY `order`.created'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for op_name,team,delivery_time,created,order_id,express_id,express_number,ship_to,province,city,district,street1,fee,item_name,price,quantity,in_quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                              'team':DEPARTMENTS.get(team[0],'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':created.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1
            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'in':in_quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_paidan_zaitu.html',data=_data,period=period)

#物流派单对帐在途明细表
@report.route('/financial/paidan/dzzaitu')
@admin_required
def financial_report_by_paidan_dzzaitu():
    period = ''
    _conditions = ['`order`.status=6']
    
    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`created`<="%s"'%_s_end_date)

    if not _s_start_date and not _s_end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_s_start_date if _s_start_date else u'开始',_s_end_date if _s_end_date else u'现在')

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `operator`.nickname,`order`.`team`,`order`.delivery_time,`order`.created,`order`.order_id,`express_id`,`express_number`,`ship_to`,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.in_quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.delivery_time IS NOT NULL AND `order`.arrival_time IS NOT NULL
JOIN `address` ON `order`.shipping_address_id=`address`.id
JOIN `operator` ON `operator`.id=`order`.created_by
WHERE %s
ORDER BY `order`.created'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for op_name,team,delivery_time,created,order_id,express_id,express_number,ship_to,province,city,district,street1,fee,item_name,price,quantity,in_quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                              'team':DEPARTMENTS.get(team[0],'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':created.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1
            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'in':in_quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_paidan_dzzaitu.html',data=_data,period=period)

#物流派单未对帐明细表
@report.route('/financial/paidan/pdwdz')
@admin_required
def financial_report_by_paidan_pdwdz():
    period = ''
    _conditions = ['`order`.status in (5,6,31,9,7,32,33,34)']
    #_conditions = ['`order`.status =9']
    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`order`.`created`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`order`.`created`<="%s"'%_s_end_date)

    if not _s_start_date and not _s_end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_s_start_date if _s_start_date else u'开始',_s_end_date if _s_end_date else u'现在')

    express_id = request.args.get('express_id',0)
    if express_id:
        _conditions.append('`order`.express_id=%s'%express_id)

    _sql = '''SELECT `order`.status,`operator`.nickname,`order`.`team`,`order`.delivery_time,`order`.created,`order`.order_id,`express_id`,`express_number`,`ship_to`,`province`,`city`,`district`,`street1`,`order`.item_fee-`order`.discount_fee,`order_item`.name,`order_item`.price,`order_item`.quantity,`order_item`.in_quantity,`order_item`.fee FROM `order_item`
JOIN `order` ON `order_item`.order_id=`order`.order_id AND `order`.delivery_time IS NOT NULL
JOIN `address` ON `order`.shipping_address_id=`address`.id
JOIN `operator` ON `operator`.id=`order`.created_by
WHERE %s
ORDER BY `order`.created'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for status,op_name,team,delivery_time,created,order_id,express_id,express_number,ship_to,province,city,district,street1,fee,item_name,price,quantity,in_quantity,item_fee in rows:
        if not data.has_key(order_id):
            data[order_id] = {'eid':express_id,
                              'op':op_name,
                              'team':DEPARTMENTS.get(team[0],'') if team else '',
                              'ename':EXPRESS_CONFIG[int(express_id)]['name'],
                              'enum':express_number,
                              'fee':fee,
                              'id':order_id,
                              'date':created.strftime("%Y-%m-%d"),
                              'delivery_time':delivery_time.strftime("%Y-%m-%d"),
                              'items':[],
                              'ship_to':ship_to,
                              'province':province,
                              'city':city,
                              'district':district,
                              'street1':street1,
                              'status':ORDER_STATUS[status]

            }
        data[order_id]['items'].append({'name':item_name,'num':quantity,'in':in_quantity,'fee':item_fee,'price':price})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['eid'])
    return render_template('report/financial_report_by_paidan_pdwdz.html',data=_data,period=period)
#心力健销售统计
@report.route('/john/zz')
@admin_required
def john_zz():
    _conditions = []

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.created>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.created<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`order`.created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    #select count(*) from user where entries like '%A01%'
    sql = ''
    for a,b,c,d in USER_BODY_CONFIG:
        for a1,b1,c1 in c:
            sql += 'union all select \''+b1+'\',count(u.user_id) from user u where u.user_id in (select user_id from `order` where order_id in (select order_id from order_item where sku_id in (10035,10003))) and u.entries like \'%'+a1+'%\' '
    sql = sql[9:len(sql)]
    return sql

    _sql = _sql1+' union all '+_sql2#+' union all '+_sql3+' union all '+_sql4+' union all '+_sql5+' union all '+_sql6+' union all '+_sql7+' union all '+_sql8+' union all '+_sql9+' union all '+_sql10+' union all '+_sql11+' union all '+_sql12
    #return _sql
    rows = db.session.execute(_sql)
    return render_template('report/user_report_by_xlj_sale.html',rows=rows,period=period)

#气血和
@report.route('/john/qxh')
@admin_required
def join_qxh():
    goods='10001,10002,10003'
    #保健品
    goods='10029,10021,10028,10026,10024,10022,10025,10023,10027,10125,10127,10127,10123,10124'
    #化妆品
    goods='10062,10059,10058,10005,10006,10060,10007,10061,10016,10014,10015,10008,10013,10009,10011,10010,10012,10019,10018,10017,10020,10122,10030,10042'
    _conditions = ["`order`.created>\'2014-01-01\'"]
    _conditions.append('`order`.status NOT IN (1,103)','`order`.status<200')

    _sql1 = '''SELECT COUNT(distinct user.user_id),m1,m2 user_ids FROM `user`
 WHERE %s group by m1,m2 order by `user`.m1,`user`.m2'''%' AND '.join(_conditions)
    #return _sql1
    _sql2 = '''SELECT address.province,left(`order`.created,7),round(sum(`order`.item_fee),2),count(`order`.order_id) from `order` join order_item on order_item.order_id=`order`.order_id 
    join address on address.id=`order`.shipping_address_id 
         WHERE `order`.created>\'2014-01-01\' AND `order`.status NOT IN (1,103) and `order`.status<200 AND order_item.sku_id in ('''+goods+''') group by address.province,left(`order`.created,7) order by address.province'''

    #return _sql2
    totaljx = []#所有订单总额
    totalss = []#所有订单数
    
    #return _sql
    rows2 = db.session.execute(_sql2)
    return render_template('report/user_report_by_diqu.html',totaljx=totaljx,totalss=totalss,rows2=rows2)

#空盒送礼登记表
@report.route('/yy/khsl')
@admin_required
def yy_khsl():
    _conditions = ['`qxhkjdj`.status=1']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`qxhkjdj`.date>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`qxhkjdj`.date<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`qxhkjdj`.date>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    rows = QXHKHDJ.query.filter(db.and_(*_conditions))
    rowsc = QXHKHDJ.query.filter(db.and_(*_conditions)).count();
    print rowsc
    return render_template('report/yy_report_by_khsl.html',rowsc=rowsc,rows=rows,period=period)


@report.route('/pharmacy')
@admin_required
def pharmacy_report():
    return render_template('report/pharmacy_report.html')



@report.route('/pharmacy/shuju')
@admin_required
def pharmacy_report_by_shuju():
    areas = db.session.execute('select distinct area from user where qxhdm_time > 0')
    promoterss = db.session.execute('select distinct promoters from user where qxhdm_time > 0')
    pharmacys = db.session.execute('select distinct pharmacy from user where qxhdm_time > 0')
    _conditions = ['`user`.qxhdm_time > 0']
    area = request.args.get('area','')
    if area:
        _conditions.append('`user`.area="%s"'%area)
    promoters = request.args.get('promoters','')
    if promoters:
        _conditions.append('`user`.promoters="%s"'%promoters)
    pharmacy = request.args.get('pharmacy','')
    if pharmacy:
        _conditions.append('`user`.pharmacy="%s"'%pharmacy)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.qxhdm_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.qxhdm_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.qxhdm_time>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
                user.qxhdm_time,
                user.area,
                user.promoters,
                user.pharmacy,
                user.pharmacystores,
                user.name,
                user.phone,
                sum(`qxhdm_orderyf`.bigcount) bigcount,
                sum(`qxhdm_orderyf`.smallcount) smallcount,
                sum(`qxhdm_orderyf`.qizaocount) qizaocount,
                user.disease
                 FROM `user` left join qxhdm_orderyf on qxhdm_orderyf.user_id=user.user_id
                WHERE
                %s
                GROUP BY `user`.user_id
                order BY `user`.qxhdm_time desc'''%' AND '.join(_conditions)
    print _sql
    data = db.session.execute(_sql)
    bigcounts = []
    smallcounts = []
    qizaocounts = []
    return render_template('report/pharmacy_report_by_shuju.html',qizaocounts=qizaocounts,smallcounts=smallcounts,bigcounts=bigcounts,areas=areas,pharmacys=pharmacys,promoterss=promoterss,data=data,period=period)

@report.route('/pharmacy/shujufankui')
@admin_required
def pharmacy_report_by_shujufankui():
    areas = db.session.execute('select distinct area from user where qxhdm_time > 0')
    promoterss = db.session.execute('select distinct promoters from user where qxhdm_time > 0')
    pharmacys = db.session.execute('select distinct pharmacy from user where qxhdm_time > 0')
    _conditions = ['`user`.qxhdm_time > 0']
    area = request.args.get('area','')
    if area:
        _conditions.append('`user`.area="%s"'%area)
    promoters = request.args.get('promoters','')
    if promoters:
        _conditions.append('`user`.promoters="%s"'%promoters)
    pharmacy = request.args.get('pharmacy','')
    if pharmacy:
        _conditions.append('`user`.pharmacy="%s"'%pharmacy)

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.qxhdm_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.qxhdm_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.qxhdm_time>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
        user.area,
        user.promoters,
        user.pharmacy,
        user.pharmacystores,
        count(1) allusers,
        count(case WHEN  is_valid = 1 then 1 end) as `validusers`,
        count(case WHEN is_valid = 2 then 1 end) as `notvalidusers`
        FROM `user`
        WHERE
        %s
        GROUP BY user.area,
        user.promoters,
        user.pharmacy,
        user.pharmacystores
        ORDER BY user.area,
        user.promoters,
        user.pharmacy,
        user.pharmacystores'''%' AND '.join(_conditions)
    print _sql
    data = db.session.execute(_sql)
    allusers = []
    validusers = []
    notvalidusers = []
    return render_template('report/pharmacy_report_by_shujufankui.html',notvalidusers=notvalidusers,validusers=validusers,allusers=allusers,areas=areas,pharmacys=pharmacys,promoterss=promoterss,data=data,period=period)

@report.route('/pharmacy/fugou')
@admin_required
def pharmacy_report_by_fugou():
    areas = db.session.execute('select distinct area from user where qxhdm_time > 0')
    pharmacys = db.session.execute('select distinct pharmacy from user where qxhdm_time > 0')
    _conditions = ['`user`.qxhdm_time > 0']
    _conditions2 = []
    area = request.args.get('area','')
    if area:
        _conditions.append('`user`.area="%s"'%area)
    pharmacy = request.args.get('pharmacy','')
    if pharmacy:
        _conditions.append('`user`.pharmacy="%s"'%pharmacy)


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions2.append('`user`.qxhdm_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions2.append('`user`.qxhdm_time<="%s"'%_end_date)
    _today = datetime.now().strftime('%Y-%m-%d')
    if not _start_date and not _end_date:        
        _conditions2.append('`user`.qxhdm_time>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
        user.area,
        user.pharmacy,
        user.pharmacystores,
        count(case WHEN %s then 1 end) as `validusers`,
        count(1) allusers,
        count(case WHEN %s then 1 end) as `fugou`,
        count(case WHEN `user`.is_isable = 1 then 1 end) as `notvalidusers`
        FROM `user`
        WHERE
        %s
        GROUP BY user.area,
        user.pharmacy,
        user.pharmacystores
        ORDER BY user.area,
        user.pharmacy,
        user.pharmacystores'''%(' AND '.join(_conditions2),' AND '.join(_conditions2).replace('qxhdm_time','lastfugou_time'),' AND '.join(_conditions))

    print _sql
    data = db.session.execute(_sql)
    validusers = []
    allusers = []
    fugou = []
    notvalidusers = []
    return render_template('report/pharmacy_report_by_fugou.html',notvalidusers=notvalidusers,fugou=fugou,allusers=allusers,validusers=validusers,areas=areas,pharmacys=pharmacys,data=data,period=period)
#复购预判明细
@report.route('/pharmacy/fugouypmx')
@admin_required
def pharmacy_report_by_fugouypmx():
    #areas = db.session.execute('select distinct area from user where qxhdm_time > 0')
    pharmacys = db.session.execute('select distinct pharmacy from user where qxhdm_time > 0')
    _conditions = ['`user`.qxhdm_time > 0']
    _conditions = []
    area = request.args.get('area','')
    if area:
        _conditions.append('`user`.area="%s"'%area)
    pharmacy = request.args.get('pharmacy','')
    if pharmacy:
        _conditions.append('`user`.pharmacy="%s"'%pharmacy)


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`qxhdm_orderyf`.created>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`qxhdm_orderyf`.created<="%s"'%_end_date)
    _today = datetime.now().strftime('%Y-%m-%d')
    if not _start_date and not _end_date:        
        _conditions.append('`qxhdm_orderyf`.created>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    data = QXHDM_Orderyf.query.outerjoin(User,User.user_id==QXHDM_Orderyf.user_id).filter(db.and_(*_conditions))
    print data
    return render_template('report/pharmacy_report_by_fugouypmx.html',pharmacys=pharmacys,data=data,period=period)
#服务组复购预判明细表
@report.route('/pharmacy/khfgypmx')
@admin_required
def pharmacy_report_by_khfgypmx():

    #仅允许管理本部门员工数据
    if not current_user.is_admin and current_user.team:
        operators = Operator.query.filter(db.and_(Operator.team.like(current_user.team+'%'),Operator.assign_user_type>0,Operator.status<>9))
        #op_ids = [op.id for op in operators]
        #_conditions.append(User.assign_operator_id.in_(op_ids))
    else:
        operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9)

    _conditions = ['`user`.user_id not in (select user_id from user_servicelz)']
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`user`.assign_operator_id="%s"'%assign_operator_id)


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`qxhdm_orderyf`.created>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`qxhdm_orderyf`.created<="%s"'%_end_date)
    _today = datetime.now().strftime('%Y-%m-%d')
    if not _start_date and not _end_date:        
        _conditions.append('`qxhdm_orderyf`.created>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    data = QXHDM_Orderyf.query.outerjoin(User,User.user_id==QXHDM_Orderyf.user_id).filter(db.and_(*_conditions))#.order_by(User.origin,User.area,User.assign_operator_id)

    return render_template('report/pharmacy_report_by_khfgypmx.html',operators=operators,data=data,period=period)
#空盒换大礼服务明细表
@report.route('/pharmacy/khfwmx')
@admin_required
def pharmacy_report_by_khfwmx():

    _conditions = ['`u`.origin = 19','`u`.user_id not in (select user_id from user_servicelz)']
    area = request.args.get('area','')
    if area:
        _conditions.append('`u`.area="%s"'%area)
    register = request.args.get('register','')
    if register == '1':
        _conditions.append('`kh`.id>0')
    if register == '2':
        _conditions.append('`kh`.id is null')

    phone = request.args.get('phone', None)
    if phone:
        _conditions.append('`u`.phone="%s"'%phone)


    communication = request.args.get('communication','')
    if communication:
        _conditions.append('`u`.communication="%s"'%communication)

    isable_reason = request.args.get('isable_reason','')
    if isable_reason:
        _conditions.append('`u`.isable_reason="%s"'%isable_reason)

    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`u`.assign_operator_id="%s"'%assign_operator_id)



    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('kh.date>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('kh.date<="%s"'%_end_date)
    
    _start_fpdate = request.args.get('start_fpdate','')
    if _start_fpdate:
        _conditions.append('`u`.assign_time>="%s"'%_start_fpdate)

    _end_fpdate = request.args.get('end_fpdate','')
    if _end_fpdate:
        _conditions.append('`u`.assign_time<="%s"'%_end_fpdate)
    _today = datetime.now().strftime('%Y-%m-%d')
    if not _start_fpdate and not _end_fpdate:        
        _conditions.append('`u`.assign_time>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_fpdate if _start_fpdate else u'开始',_end_fpdate if _end_fpdate else u'现在')


    _sql = 'select u.name,u.phone,u.assign_time,u.area,(select count(*) from qxhdm_orderyf where user_id=u.user_id) fgypcount,u.communication,u.isable_reason,kh.id,kh.reason,kh.receive,o.nickname,kh.date from user u left join operator o on o.id=u.assign_operator_id left join qxhkjdj kh on u.user_id=kh.user_id where %s order by assign_time'%' AND '.join(_conditions)
    print _sql
    #data = User.query.filter(db.and_(*_conditions))
    data = db.session.execute(_sql)
    total = []
    #print data.length()
    operators = Operator.query.filter(Operator.team=='C3')
    return render_template('report/pharmacy_report_by_khfwmx.html',operators=operators,data=data,period=period,total=total)

#复购统计
@report.route('/yy/fgtj')
@admin_required
def yy_fgtj():
    _conditions2 = ['user_id not in (select user_id from user_servicelz)']
    _conditions = []
    area = request.args.get('area','')
    if area:
        _conditions2.append('area="%s"'%area)
    user_origin = request.args.get('user_origin','')
    if user_origin:
        _conditions2.append('origin=%s'%user_origin)
    user_where = ' AND '.join(_conditions2)
    if user_where:
        user_where = ' AND '+user_where
    #print user_where
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('created>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('created<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('created>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _sql = 'select nickname,id from operator where assign_user_type=5'
    rows = db.session.execute(_sql)
    _sql = ''
    for r in rows:
        _sql += ''' UNION all SELECT '%s',count(*),sum(bigcount),sum(mediumcount),sum(smallcount),0 from user_tjfg where user_id in (SELECT user_id from user where assign_operator_id=%s %s) and %s
         UNION all SELECT '%s',count(*),sum(bigcount),sum(mediumcount),sum(smallcount),sum(qizaocount) from qxhdm_orderyf where user_id in (SELECT user_id from user where assign_operator_id=%s %s) and %s
'''%(r[0],r[1],user_where,' AND '.join(_conditions),r[0],r[1],user_where,' AND '.join(_conditions))
    #return _sql[10:]
    rows = db.session.execute(_sql[10:])
    tjcount = []
    tjbig = []
    tjme = []
    tjsmall = []
    fgcount = []
    fgbig = []
    fgme = []
    fgsmall = []
    fgqizao = []
    return render_template('report/user_report_by_fwfg.html',tjcount=tjcount,tjbig=tjbig,tjme=tjme,tjsmall=tjsmall,fgcount=fgcount,fgbig=fgbig,fgme=fgme,fgsmall=fgsmall,fgqizao=fgqizao,rows=rows,period=period)
#维护
@report.route('/weihu')
@admin_required
def weihu_report():
    #db.session.execute("call weihu()")
    return render_template('report/weihu_report.html')
@report.route('/weihu1')
@admin_required
def weihu_report1():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_weihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_weihu`.date="%s"'%yesterday)
    rows = Weihu.query.filter(*_conditions)
    return render_template('report/weihu_report1.html',rows=rows)

@report.route('/weihu2')
@admin_required
def weihu_report2():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_weihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_weihu`.date="%s"'%yesterday)
    rows = Weihu.query.filter(*_conditions)
    return render_template('report/weihu_report2.html',rows=rows)
@report.route('/weihuyeji')
@admin_required
def weihu_reportyeji():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_weihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_weihu`.date="%s"'%yesterday)
    rows = Weihu.query.filter(*_conditions)
    return render_template('report/weihu_reportyeji.html',rows=rows)
@report.route('/weihucpgc')
@admin_required
def weihu_reportcpgc():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_weihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_weihu`.date="%s"'%yesterday)
    rows = Weihu.query.filter(*_conditions)
    return render_template('report/weihu_reportcpgc.html',rows=rows)


#外呼
@report.route('/waihu')
@admin_required
def waihu_report():
    #db.session.execute("call weihu()")
    return render_template('report/waihu_report.html')
@report.route('/waihu1')
@admin_required
def waihu_report1():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_waihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_waihu`.date="%s"'%yesterday)
    rows = Waihu.query.filter(*_conditions)
    return render_template('report/waihu_report1.html',rows=rows)
@report.route('/waihu2')
@admin_required
def waihu_report2():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_waihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_waihu`.date="%s"'%yesterday)
    rows = Waihu.query.filter(*_conditions)
    return render_template('report/waihu_report2.html',rows=rows)
@report.route('/waihu3')
@admin_required
def waihu_report3():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_waihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_waihu`.date="%s"'%yesterday)
    rows = Waihu.query.filter(*_conditions)
    return render_template('report/waihu_report3.html',rows=rows)
@report.route('/waihu4')
@admin_required
def waihu_report4():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_waihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_waihu`.date="%s"'%yesterday)
    rows = Waihu.query.filter(*_conditions)
    return render_template('report/waihu_report4.html',rows=rows)
@report.route('/waihu5')
@admin_required
def waihu_report5():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_waihu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_waihu`.date="%s"'%yesterday)
    rows = Waihu.query.filter(*_conditions)
    return render_template('report/waihu_report5.html',rows=rows)


#接线
@report.route('/jiexian')
@admin_required
def jiexian_report():
    #db.session.execute("call weihu()")
    return render_template('report/jiexian_report.html')
@report.route('/jiexian1')
@admin_required
def jiexian_report1():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_jiexian`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_jiexian`.date="%s"'%yesterday)
    rows = Jiexian.query.filter(*_conditions)
    return render_template('report/jiexian_report1.html',rows=rows)
@report.route('/jiexian2')
@admin_required
def jiexian_report2():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_jiexian`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        print yesterday
        _conditions.append('`report_jiexian`.date="%s"'%yesterday)
    rows = Jiexian.query.filter(*_conditions)
    return render_template('report/jiexian_report2.html',rows=rows)

#外呼
@report.route('/fuwu')
@admin_required
def fuwu_report():
    #db.session.execute("call weihu()")
    return render_template('report/fuwu_report.html')
@report.route('/fuwu1')
@admin_required
def fuwu_report1():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_fuwu`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_fuwu`.date="%s"'%yesterday)
    rows = Fuwu.query.filter(*_conditions)
    return render_template('report/fuwu_report1.html',rows=rows)
@report.route('/fuwu2')
@admin_required
def fuwu_report2():
    #db.session.execute("call weihu()")
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`report_fuwu2`.date="%s"'%_start_date)
    else:
        _now = datetime.now()
        _yesterday = _now+timedelta(days=-1)
        yesterday = _yesterday.strftime('%Y-%m-%d')
        _conditions.append('`report_fuwu2`.date="%s"'%yesterday)
    rows = Fuwu2.query.filter(*_conditions)
    return render_template('report/fuwu_report2.html',rows=rows)


@report.route('/dlb')
@admin_required
def dlb_report():
    return render_template('report/dlb_report.html')

@report.route('/dlb/zt')
@admin_required
def dlb_zt():
    _conditions = []
    _op_sql = 'SELECT id,nickname FROM `operator` WHERE role_id=101'
    _ops = db.session.execute(_op_sql)    
    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`assign_operator_id`=%d'%int(op_id))


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('dlb_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('dlb_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('dlb_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _sql = 'SELECT dlb_time,count(*) as total,SUM(CASE WHEN dlb_valid=2 THEN 1 ELSE 0 END) as wx,SUM(CASE WHEN dlb_new=2 THEN 1 ELSE 0 END) as old,SUM(CASE WHEN dlb_new=1 THEN 1 ELSE 0 END) as new from user where dlb_type>0 and %s GROUP BY dlb_time'%' AND '.join(_conditions)
    #print _sql
    #data = User.query.filter(db.and_(*_conditions))
    data = db.session.execute(_sql)
    total = []
    wxtotal = []
    oldtotal = []
    newtotal = []

    return render_template('report/dlb_zt.html',data=data,period=period,ops=_ops
,total=total,wxtotal=wxtotal,oldtotal=oldtotal,newtotal=newtotal)


@report.route('/dlb/new')
@admin_required
def dlb_new():
    _conditions = []
    _op_sql = 'SELECT id,nickname FROM `operator` WHERE role_id=101'
    _ops = db.session.execute(_op_sql)    
    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`assign_operator_id`=%d'%int(op_id))

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('dlb_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('dlb_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('dlb_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _sql = 'SELECT dlb_time,count(*) as total,SUM(CASE WHEN dlb_connect=1 THEN 1 ELSE 0 END) as connect,SUM(CASE WHEN (SELECT count(order_id) from `order` WHERE order_mode=18 and status not in (1,103) and `order`.user_id=`user`.user_id) THEN 1 ELSE 0 END) as sl,SUM(CASE WHEN (SELECT count(order_id) from `order` WHERE order_mode=19 and status not in (1,103) and `order`.user_id=`user`.user_id) THEN 1 ELSE 0 END) as sccj from user where dlb_type>0 and dlb_new=1 and %s GROUP BY dlb_time'%' AND '.join(_conditions)
    #print _sql
    #data = User.query.filter(db.and_(*_conditions))
    data = db.session.execute(_sql)
    total = []
    jttotal = []
    sltotal = []
    sccjtotal = []


    return render_template('report/dlb_new.html',data=data,period=period,ops=_ops
,total=total,jttotal=jttotal,sltotal=sltotal,sccjtotal=sccjtotal)


@report.route('/dlb/jinxian')
@admin_required
def dlb_jinxian():
    _conditions = []
    _op_sql = 'SELECT id,nickname FROM `operator` WHERE role_id=101'
    _ops = db.session.execute(_op_sql)    
    op_id = request.args.get('op',0)
    if op_id:
        _conditions.append('`assign_operator_id`=%d'%int(op_id))


    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('dlb_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('dlb_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('dlb_time>="%s 00:00:00"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _sql = '''SELECT dlb_time,
    SUM(CASE WHEN dlb_type=2 THEN 1 ELSE 0 END) as wxtotal,
    SUM(CASE WHEN (dlb_type=2 and dlb_valid=2) THEN 1 ELSE 0 END) as wxwx,
    SUM(CASE WHEN (dlb_type=2 and dlb_new=2) THEN 1 ELSE 0 END) as wxold,
    SUM(CASE WHEN (dlb_type=2 and dlb_new=1) THEN 1 ELSE 0 END) as wxnew,
    SUM(CASE WHEN (dlb_type=2 and dlb_connect=1) THEN 1 ELSE 0 END) as wxconnect,
    SUM(CASE WHEN (SELECT count(order_id) from `order` WHERE order_mode=18 and status not in (1,103) and `order`.user_id=`user`.user_id and `user`.dlb_type=2) THEN 1 ELSE 0 END) as wxsl,
    SUM(CASE WHEN (SELECT count(order_id) from `order` WHERE order_mode=19 and status not in (1,103) and `order`.user_id=`user`.user_id and `user`.dlb_type=2) THEN 1 ELSE 0 END) as wxsccj,
    SUM(CASE WHEN dlb_type=1 THEN 1 ELSE 0 END) as lytotal,
    SUM(CASE WHEN (dlb_type=1 and dlb_valid=2) THEN 1 ELSE 0 END) as lywx,
    SUM(CASE WHEN (dlb_type=1 and dlb_new=2) THEN 1 ELSE 0 END) as lyold,
    SUM(CASE WHEN (dlb_type=1 and dlb_new=1) THEN 1 ELSE 0 END) as lynew,
    SUM(CASE WHEN (dlb_type=1 and dlb_connect=1) THEN 1 ELSE 0 END) as lyconnect,
    SUM(CASE WHEN (SELECT count(order_id) from `order` WHERE order_mode=18 and status not in (1,103) and `order`.user_id=`user`.user_id and `user`.dlb_type=1) THEN 1 ELSE 0 END) as lysl,
    SUM(CASE WHEN (SELECT count(order_id) from `order` WHERE order_mode=19 and status not in (1,103) and `order`.user_id=`user`.user_id and `user`.dlb_type=1) THEN 1 ELSE 0 END) as lysccj
     from user where dlb_type>0 and %s GROUP BY dlb_time'''%' AND '.join(_conditions)
        #print _sql
        #data = User.query.filter(db.and_(*_conditions))
    
    data = db.session.execute(_sql)

    lytotal = []
    lywx = []
    lyold = []
    lynew = []
    lyconnect = []
    lysl = []
    lysccj = []
    wxtotal = []
    wxwx = []
    wxold = []
    wxnew = []
    wxconnect = []
    wxsl = []
    wxsccj = []

    return render_template('report/dlb_jinxian.html',data=data,period=period,ops=_ops
,lytotal=lytotal,lywx=lywx,lyold=lyold,lynew=lynew,lyconnect=lyconnect,lysl=lysl,lysccj=lysccj
,wxtotal=wxtotal,wxwx=wxwx,wxold=wxold,wxnew=wxnew,wxconnect=wxconnect,wxsl=wxsl,wxsccj=wxsccj)



#刮刮卡进线
@report.route('/sale/scratchjx')
@admin_required
def sale_scratchjx():
    _conditions = ['`user`.user_id not in (select user_id from user_servicelz)']#['`user`.status=1']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.assign_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.assign_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.assign_time>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = 'select nickname,id from operator where assign_user_type=5 and id in(select assign_operator_id from user where origin=27 and %s)'%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    _sql = ''
    operatorcount = 0
    for r in rows:
        operatorcount += 1
        _sql1 = " UNION all SELECT '%s',count(*),0,0 from `user` where assign_operator_id=%s and origin=27 and %s"%(r[0],r[1],' AND '.join(_conditions))
        _sql2 = " UNION all SELECT '%s',count(*),0,0 from `user` where assign_operator_id=%s and origin=27 and %s and user_id in (SELECT user_id from `order` where order_mode=25 and `status` not in (1,103))"%(r[0],r[1],' AND '.join(_conditions))
        _sql3 = " UNION all SELECT '%s',count(*),0,0 from `user` where assign_operator_id=%s and origin=27 and %s and user_id in (SELECT user_id from `order` where order_mode=25 and `arrival_time` IS NOT NULL and `status` not in (1,103))"%(r[0],r[1],' AND '.join(_conditions))
        _sql4 = " UNION all select '%s',count(*),0,0 from qxhdm_orderyf where user_id in (SELECT user_id from `user` where assign_operator_id=%s and origin=27 and %s)"%(r[0],r[1],' AND '.join(_conditions))
        _sql5 = " UNION all select '%s',sum(bigcount),sum(mediumcount),sum(smallcount) from qxhdm_orderyf where user_id in (SELECT user_id from `user` where assign_operator_id=%s and origin=27 and %s)"%(r[0],r[1],' AND '.join(_conditions))
        _sql += _sql1+_sql2+_sql3+_sql4+_sql5
    #return str(operatorcount)
    #return _sql
    if operatorcount:
        data = db.session.execute(_sql[10:])
    else:
        data = []
    return render_template('report/sale_report_by_scratchjx.html',di=0,data=data,operatorcount=operatorcount,period=period)

#刮刮卡明细
@report.route('/sale/scratchmx')
@admin_required
def sale_scratchmx():
    _conditions = ['`user`.user_id not in (select user_id from user_servicelz)']#['`user`.status=1']
   # _conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.assign_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.assign_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.assign_time>="%s"'%_today)
        period = _today

    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT name,phone,assign_time,area,(SELECT count(order_id) from `order` WHERE order_mode=25 and `order`.user_id=`user`.user_id and status not in (1,103)) as sfdj,(SELECT count(order_id) from `order` WHERE order_mode=25 and `order`.user_id=`user`.user_id and `arrival_time` IS NOT NULL and status not in (1,103)) as sfsh,(SELECT count(id) from `qxhdm_orderyf` WHERE qxhdm_orderyf.user_id=`user`.user_id) as fgcs,intent_level,isable_reason,operator.nickname,(SELECT max(created) from `order` WHERE order_mode=25 and `order`.user_id=`user`.user_id and status not in (1,103)) as djtime FROM `user` LEFT JOIN operator ON operator.id=`user`.assign_operator_id where origin=27 and %s'''%' AND '.join(_conditions)
    #return _sql
    data = db.session.execute(_sql)
    return render_template('report/sale_report_by_scratchmx.html',data=data,period=period)

#刮刮卡进线区域划分
@report.route('/sale/scratchqyjx')
@admin_required
def sale_scratchqyjx():
    _conditions = ['`user`.user_id not in (select user_id from user_servicelz)']#['`user`.status=1']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.assign_time>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.assign_time<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.assign_time>="%s"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = 'select distinct area from user where origin=27 and %s'%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    _sql = ''
    operatorcount = 0
    for r in rows:
        operatorcount += 1
        if r[0] is None:
            area = 'null'
        else:
            area = r[0]
        if r[0] is None:
            _sql1 = " UNION all SELECT '%s',count(*),0,0 from `user` where area is null and origin=27 and %s"%(r[0],' AND '.join(_conditions))
            _sql2 = " UNION all SELECT '%s',count(*),0,0 from `user` where area is null and origin=27 and %s and user_id in (SELECT user_id from `order` where order_mode=25 and `status` not in (1,103))"%(r[0],' AND '.join(_conditions))
            _sql3 = " UNION all SELECT '%s',count(*),0,0 from `user` where area is null and origin=27 and %s and user_id in (SELECT user_id from `order` where order_mode=25 and `arrival_time` IS NOT NULL and `status` not in (1,103))"%(r[0],' AND '.join(_conditions))
            _sql4 = " UNION all select '%s',count(*),0,0 from qxhdm_orderyf where user_id in (SELECT user_id from `user` where area is null and origin=27 and %s)"%(r[0],' AND '.join(_conditions))
            _sql5 = " UNION all select '%s',sum(bigcount),sum(mediumcount),sum(smallcount) from qxhdm_orderyf where user_id in (SELECT user_id from `user` where area is null and origin=27 and %s)"%(r[0],' AND '.join(_conditions))
        else:          
            _sql1 = " UNION all SELECT '%s',count(*),0,0 from `user` where area='%s' and origin=27 and %s"%(r[0],area,' AND '.join(_conditions))
            _sql2 = " UNION all SELECT '%s',count(*),0,0 from `user` where area='%s' and origin=27 and %s and user_id in (SELECT user_id from `order` where order_mode=25 and `status` not in (1,103))"%(r[0],area,' AND '.join(_conditions))
            _sql3 = " UNION all SELECT '%s',count(*),0,0 from `user` where area='%s' and origin=27 and %s and user_id in (SELECT user_id from `order` where order_mode=25 and `arrival_time` IS NOT NULL and `status` not in (1,103))"%(r[0],area,' AND '.join(_conditions))
            _sql4 = " UNION all select '%s',count(*),0,0 from qxhdm_orderyf where user_id in (SELECT user_id from `user` where area='%s' and origin=27 and %s)"%(r[0],area,' AND '.join(_conditions))
            _sql5 = " UNION all select '%s',sum(bigcount),sum(mediumcount),sum(smallcount) from qxhdm_orderyf where user_id in (SELECT user_id from `user` where area='%s' and origin=27 and %s)"%(r[0],area,' AND '.join(_conditions))
            
        _sql += _sql1+_sql2+_sql3+_sql4+_sql5

    #return str(operatorcount)
    #return _sql
    if operatorcount:
        data = db.session.execute(_sql[10:])
    else:
        data = []
    return render_template('report/sale_report_by_scratchqyjx.html',di=0,data=data,operatorcount=operatorcount,period=period)


@report.route('/servicelz')
@admin_required
def servicelz_report():
    return render_template('report/servicelz_report.html')

@report.route('/servicelz/mx')
@admin_required
def servicelz_report_mx():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user_servicelz`.`time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user_servicelz`.`time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user_servicelz`.`time`>="%s 00:00:00"'%_today)
        _conditions.append('`user_servicelz`.`time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`user_servicelz`.`assign_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`user_servicelz`.`assign_time`<="%s"'%_s_end_date)


    _sql = '''select `user`.`name`,`user`.phone,`user`.area,`user`.origin,(SELECT count(id) from `qxhdm_orderyf` WHERE qxhdm_orderyf.user_id=`user_servicelz`.user_id) as fgcs,`user_servicelz`.intent_level,`user`.is_valid,`user_servicelz`.assign_time,`user_servicelz`.time from `user_servicelz` LEFT JOIN `user` ON `user`.user_id=`user_servicelz`.user_id where %s '''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_mx.html',rows=rows,period=period)

@report.route('/servicelz/tj')
@admin_required
def servicelz_report_tj():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = []
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user_servicelz`.`time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user_servicelz`.`time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user_servicelz`.`time`>="%s 00:00:00"'%_today)
        _conditions.append('`user_servicelz`.`time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _s_start_date = request.args.get('s_start_date','')
    if _s_start_date:
        _conditions.append('`user_servicelz`.`assign_time`>="%s"'%_s_start_date)

    _s_end_date = request.args.get('s_end_date','')
    if _s_end_date:
        _conditions.append('`user_servicelz`.`assign_time`<="%s"'%_s_end_date)


    _sql = '''select `user`.area,`user`.origin,count(`user`.user_id) as sjl,count(`qxhdm_orderyf`.id) as fgcs from `user` LEFT JOIN `qxhdm_orderyf` ON `user`.user_id=`qxhdm_orderyf`.user_id JOIN `user_servicelz` ON `user_servicelz`.user_id=`user`.user_id where `user`.user_id in (SELECT user_id from user_servicelz) and %s group by `user`.area,`user`.origin'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_tj.html',rows=rows,period=period)

#空盒周报
@report.route('/servicelz/khzb')
@admin_required
def servicelz_report_khzb():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=19']
    _conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    _conditions2 = ['`user`.origin=19']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.`assign_time`>="%s"'%_start_date)
        _conditions2.append('`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.`assign_time`<="%s"'%_end_date)
        _conditions2.append('`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`user`.`assign_time`<="%s 23:59:59"'%_today)
        _conditions2.append('`created`>="%s 00:00:00"'%_today)
        _conditions2.append('`created`<="%s 23:59:59"'%_today)


        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT `user`.area,count(`user`.user_id) as jxzs,
SUM(CASE WHEN (SELECT count(id) from qxhkjdj where qxhkjdj.user_id=`user`.user_id)>0 THEN 1 ELSE 0 END) as ydj,
SUM(CASE WHEN `user`.intent_level='A' THEN 1 ELSE 0 END) as zsls,SUM(CASE WHEN `user`.intent_level='F' THEN 1 ELSE 0 END) as fqsj
 from `user` where %s GROUP BY `user`.area ORDER BY area'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    _sql2 = 'SELECT `user`.area,COUNT(qxhdm_orderyf.id) as fgds from user LEFT JOIN qxhdm_orderyf on qxhdm_orderyf.user_id=`user`.user_id where %s GROUP BY `user`.area ORDER BY area'%' AND '.join(_conditions2)
    rows2 = db.session.execute(_sql2)
    #print dir(rows)
    return render_template('report/servicelz_report_khzb.html',rows=rows,rows2=rows2,period=period)


#空盒月报
@report.route('/servicelz/khyb')
@admin_required
def servicelz_report_khyb():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=19']
    _conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.`assign_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.`assign_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`user`.`assign_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT area,count(*) as jxzs,SUM(CASE WHEN (SELECT count(id) from qxhkjdj where qxhkjdj.user_id=`user`.user_id)>0 THEN 1 ELSE 0 END) as ydj
,SUM(CASE WHEN (SELECT count(id) from qxhkjdj where qxhkjdj.user_id=`user`.user_id and qxhkjdj.receive=1)>0 THEN 1 ELSE 0 END) as ydjlq,
SUM(CASE WHEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id)>0 THEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id) ELSE 0 END) as fgds
,SUM(CASE WHEN intent_level='A' THEN 1 ELSE 0 END) as zsls,SUM(CASE WHEN intent_level='F' THEN 1 ELSE 0 END) as fqsj
 from `user` where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area

'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_khyb.html',rows=rows,period=period)

#空盒月报
@report.route('/servicelz/khyblz')
@admin_required
def servicelz_report_khyblz():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=19']
    #_conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`us`.`assign_time`>="%s"'%_start_date)
    
    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`us`.`assign_time`<="%s"'%_end_date)
    
    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`us`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`us`.`assign_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _start_date1 = request.args.get('start_date1','')
    if _start_date1:
        _conditions.append('`us`.`time`>="%s"'%_start_date1)
    
    _end_date1 = request.args.get('end_date1','')
    if _end_date1:
        _conditions.append('`us`.`time`<="%s"'%_end_date1)
    
    

    _sql = '''SELECT area,count(*) as jxzs,SUM(CASE WHEN (SELECT count(id) from qxhkjdj where qxhkjdj.user_id=`user`.user_id)>0 THEN 1 ELSE 0 END) as ydj
,SUM(CASE WHEN (SELECT count(id) from qxhkjdj where qxhkjdj.user_id=`user`.user_id and qxhkjdj.receive=1)>0 THEN 1 ELSE 0 END) as ydjlq,
SUM(CASE WHEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id)>0 THEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id) ELSE 0 END) as fgds
,SUM(CASE WHEN us.intent_level='A' THEN 1 ELSE 0 END) as zsls,SUM(CASE WHEN us.intent_level='F' THEN 1 ELSE 0 END) as fqsj
 from `user` LEFT JOIN user_servicelz us on `user`.user_id=us.user_id where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area

'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_khyblz.html',rows=rows,period=period)

#终端月报
@report.route('/servicelz/zdyb')
@admin_required
def servicelz_report_zdyb():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=18']
    _conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.`assign_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.`assign_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`user`.`assign_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT area,count(*) as jxzs
,SUM(CASE WHEN is_valid=1 THEN 1 ELSE 0 END) as yxl
,SUM(CASE WHEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id)>0 THEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id) ELSE 0 END) as fgds
,SUM(CASE WHEN intent_level='F' THEN 1 ELSE 0 END) as lsl
 from `user` where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area

'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_zdyb.html',rows=rows,period=period)

#终端月报
@report.route('/servicelz/zdyblz')
@admin_required
def servicelz_report_zdyblz():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=18']
    #_conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`us`.`assign_time`>="%s"'%_start_date)
    
    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`us`.`assign_time`<="%s"'%_end_date)
    
    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`us`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`us`.`assign_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')
    
    _start_date1 = request.args.get('start_date1','')
    if _start_date1:
        _conditions.append('`us`.`time`>="%s"'%_start_date1)
    
    _end_date1 = request.args.get('end_date1','')
    if _end_date1:
        _conditions.append('`us`.`time`<="%s"'%_end_date1)
    
    

    _sql = '''SELECT area,count(*) as jxzs
,SUM(CASE WHEN is_valid=1 THEN 1 ELSE 0 END) as yxl
,SUM(CASE WHEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id)>0 THEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id) ELSE 0 END) as fgds
,SUM(CASE WHEN (is_valid=1 and (us.intent_level='A' or us.intent_level='F')) THEN 1 ELSE 0 END) as lsl
 from `user` LEFT JOIN user_servicelz us on `user`.user_id=us.user_id where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area

'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_zdyblz.html',rows=rows,period=period)


#刮刮卡周报
@report.route('/servicelz/ggkzb')
@admin_required
def servicelz_report_ggkzb():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=27']
    _conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    _conditions2 = ['`user`.origin=27']
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.`assign_time`>="%s"'%_start_date)
        _conditions2.append('`created`>="%s"'%_start_date)


    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.`assign_time`<="%s"'%_end_date)
        _conditions2.append('`created`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`user`.`assign_time`<="%s 23:59:59"'%_today)
        _conditions2.append('`created`>="%s 00:00:00"'%_today)
        _conditions2.append('`created`<="%s 23:59:59"'%_today)
        
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT area,count(*) as jxzs,SUM(CASE WHEN (SELECT count(id) from scratchdj where scratchdj.user_id=`user`.user_id)>0 THEN 1 ELSE 0 END) as ydj,
SUM(CASE WHEN intent_level='A' THEN 1 ELSE 0 END) as zsls,SUM(CASE WHEN intent_level='F' THEN 1 ELSE 0 END) as fqsj
 from `user` where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area'''
    #return _sql
    rows = db.session.execute(_sql)
    _sql2 = 'SELECT `user`.area,COUNT(qxhdm_orderyf.id) as fgds from user LEFT JOIN qxhdm_orderyf on qxhdm_orderyf.user_id=`user`.user_id where %s GROUP BY `user`.area ORDER BY area'%' AND '.join(_conditions2)
    rows2 = db.session.execute(_sql2)

    #print dir(rows)
    return render_template('report/servicelz_report_ggkzb.html',rows=rows,rows2=rows2,period=period)

#刮刮卡月报
@report.route('/servicelz/ggkyb')
@admin_required
def servicelz_report_ggkyb():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=27']
    _conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.`assign_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.`assign_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`user`.`assign_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT area,count(*) as jxzs,SUM(CASE WHEN (SELECT count(id) from scratchdj where scratchdj.user_id=`user`.user_id)>0 THEN 1 ELSE 0 END) as ydj,
SUM(CASE WHEN (SELECT count(order_id) from `order` where `order`.user_id=`user`.user_id AND `order`.order_mode=25 and `order`.`arrival_time` IS NOT NULL and `order`.`status` not in (1,103))>0 THEN 1 ELSE 0 END) as dhds,
SUM(CASE WHEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id)>0 THEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id) ELSE 0 END) as fgds
,SUM(CASE WHEN intent_level='A' THEN 1 ELSE 0 END) as zsls,SUM(CASE WHEN intent_level='F' THEN 1 ELSE 0 END) as fqsj
 from `user` where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_ggkyb.html',rows=rows,period=period)

#刮刮卡月报
@report.route('/servicelz/ggkyblz')
@admin_required
def servicelz_report_ggkyblz():
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=27']
    #_conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`us`.`assign_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`us`.`assign_time`<="%s"'%_end_date)

    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`us`.`assign_time`>="%s 00:00:00"'%_today)
        _conditions.append('`us`.`assign_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _start_date1 = request.args.get('start_date1','')
    if _start_date1:
        _conditions.append('`us`.`time`>="%s"'%_start_date1)

    _end_date1 = request.args.get('end_date1','')
    if _end_date1:
        _conditions.append('`us`.`time`<="%s"'%_end_date1)


    _sql = '''SELECT area,count(*) as jxzs,SUM(CASE WHEN (SELECT count(id) from scratchdj where scratchdj.user_id=`user`.user_id)>0 THEN 1 ELSE 0 END) as ydj,
SUM(CASE WHEN (SELECT count(order_id) from `order` where `order`.user_id=`user`.user_id AND `order`.order_mode=25 and `order`.`arrival_time` IS NOT NULL and `order`.`status` not in (1,103))>0 THEN 1 ELSE 0 END) as dhds,
SUM(CASE WHEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id)>0 THEN (SELECT count(id) fgs from qxhdm_orderyf where qxhdm_orderyf.user_id=`user`.user_id) ELSE 0 END) as fgds
,SUM(CASE WHEN us.intent_level='A' THEN 1 ELSE 0 END) as zsls,SUM(CASE WHEN us.intent_level='F' THEN 1 ELSE 0 END) as fqsj
 from `user` LEFT JOIN user_servicelz us on `user`.user_id=us.user_id where '''+' AND '.join(_conditions)+''' GROUP BY area ORDER BY area'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/servicelz_report_ggkyblz.html',rows=rows,period=period)

@report.route('/waih')
@admin_required
def waih_report():
    return render_template('report/waih_report.html')

#外呼TQ报表
@report.route('/waih/tq')
@admin_required
def waih_report_tq():
    _conditions2 = ['team like "A%" or team like "B%"']
    _conditions2.append('status <> 0')
    operators = Operator.query.filter(' AND '.join(_conditions2))

    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = ['`user`.origin=4']
    #_conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`user`.`assign_operator_id`="%s"'%assign_operator_id)
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user`.`join_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user`.`join_time`<="%s"'%_end_date)


    _sstart_date = request.args.get('sstart_date','')
    if _sstart_date:
        _conditions.append('`order`.`created`>="%s"'%_sstart_date)

    _send_date = request.args.get('send_date','')
    if _send_date:
        _conditions.append('`order`.`created`<="%s"'%_send_date)


    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user`.`join_time`>="%s 00:00:00"'%_today)
        #_conditions.append('`user`.`join_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT `user`.tq_origin,`user`.tq_type,count(`user`.user_id) as yhs,sum(`order`.item_fee) as zje,count(`order`.order_id) as zds 
    from `user` LEFT JOIN `order` ON `user`.user_id=`order`.user_id AND `order`.item_fee>0 AND `order`.`status` NOT IN (1,103)
     where '''+' AND '.join(_conditions)+''' GROUP BY `user`.tq_origin,`user`.tq_type ORDER BY `user`.tq_origin,`user`.tq_type'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/waih_report_tq.html',rows=rows,operators=operators,period=period)

#流转数据跟进统计
@report.route('/waih/lz')
@admin_required
def waih_report_lz():
    _conditions2 = ['team like "A%" or team like "B%"']
    _conditions2.append('status <> 0')
    operators = Operator.query.filter(' AND '.join(_conditions2))
    #print operators
    period = ''
    #_conditions = ['`order_log`.to_status=60','`order_log`.`order_id` = `order`.`order_id`','`order`.order_type<100']
    _conditions = []
    #_conditions.append('`user`.assign_operator_id in (SELECT id from operator where team=\'C3\')')
    
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`user`.`assign_operator_id`="%s"'%assign_operator_id)
    
    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`user_servicelz`.`time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`user_servicelz`.`time`<="%s"'%_end_date)


    _sstart_date = request.args.get('sstart_date','')
    if _sstart_date:
        _conditions.append('`user`.`assign_time`>="%s"'%_sstart_date)

    _send_date = request.args.get('send_date','')
    if _send_date:
        _conditions.append('`user`.`assign_time`<="%s"'%_send_date)


    if not _start_date and not _end_date:
        _today = datetime.now().strftime('%Y-%m-%d')
        _conditions.append('`user_servicelz`.`time`>="%s 00:00:00"'%_today)
        #_conditions.append('`user`.`join_time`<="%s 23:59:59"'%_today)
        period = _today
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')


    _sql = '''SELECT `user`.origin,user_servicelz.intent_level,count(`user`.user_id) khsl,SUM(CASE WHEN `user`.lz_valid=1 THEN 1 ELSE 0 END) as yxsl,sum(`order`.item_fee) as cjje,count(`order`.order_id) as cjds FROM `user_servicelz` LEFT JOIN `user` ON `user`.user_id=user_servicelz.user_id LEFT JOIN `order` ON `order`.user_id=user_servicelz.user_id AND `order`.`status` NOT IN (1,103)
     where '''+' AND '.join(_conditions)+''' GROUP BY `user`.origin,user_servicelz.intent_level ORDER BY `user`.origin,user_servicelz.intent_level'''
    #return _sql
    rows = db.session.execute(_sql)
    #print dir(rows)
    return render_template('report/waih_report_lz.html',rows=rows,operators=operators,period=period)


@report.route('/cy')
@admin_required
def cy_report():
    return render_template('report/cy_report.html')

#
@report.route('/cy/cy1')
@admin_required
def cy_report_1():
    rstr = request.args.items().__str__()
    if rstr != '[]':
        _conditions = ['o.`status` not in (1,102)']
        
        user_origin = request.args.get('user_origin','')
        if user_origin:
            _conditions.append('`u`.`origin`=%s'%user_origin)    
        
        user_remark = request.args.get('user_remark','')
        if user_remark:
            _conditions.append('`u`.`remark`="%s"'%user_remark)
        
        
        _start_date = request.args.get('start_date','')
        if _start_date:
            _conditions.append('o.created>="%s"'%_start_date)

        _end_date = request.args.get('end_date','')
        if _end_date:
            _conditions.append('o.created<="%s"'%_end_date)


        _sql = '''SELECT o.order_id,u.name,op.nickname,o.item_fee from `order` o LEFT JOIN `user` u on o.user_id=u.user_id LEFT JOIN operator op on op.id=u.assign_operator_id where '''+' AND '.join(_conditions)
        #return _sql
        rows = db.session.execute(_sql)
        #print dir(rows)
    else:
        rows = []
    return render_template('report/cy_report_1.html',rows=rows)

@report.route('/cy/cy2')
@admin_required
def cy_report_2():
    rstr = request.args.items().__str__()
    if rstr != '[]':
        #return rstr
        #_conditions = ['''user_id in (select user_id from user where assign_operator_id in (SELECT id from operator where team like 'C%'))''']
        _conditions = ['''user_id in (select user_id from user where user_type=2)''']
        _start_date = request.args.get('start_date','')
        if _start_date:
            _conditions.append('created>="%s"'%_start_date)
        
        _end_date = request.args.get('end_date','')
        if _end_date:
            _conditions.append('created<="%s"'%_end_date)
        
        _conditions.append("created=(SELECT max(created) from `order` as b where `order`.user_id=b.user_id)")
        rows = Order.query.filter(db.and_(*_conditions))
    else:
        rows = []
    return render_template('report/cy_report_2.html',rows=rows)



@report.route('/lqweihu')
@admin_required
def lqweihu_report():
    return render_template('report/lqweihu_report.html')

#
@report.route('/lqweihu/laiyuan')
@admin_required
def lqweihu_report_laiyuan():
    operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'))
    _conditions = [r"""op.team like 'C%'"""]
    _conditions.append('`op`.`assign_user_type`>0')
    _conditions.append('`op`.`status`<>9')

    user_origin = request.args.get('user_origin','')
    if user_origin:
        _conditions.append('`u`.`origin`=%s'%user_origin)    
    
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`u`.`assign_operator_id`=%s'%assign_operator_id)    
    
    

    _sql = '''SELECT op.id,op.nickname,u.origin,count(distinct u.user_id) as countu,count(o.order_id) as counto,IFNULL(sum(o.item_fee),0) as sumo from operator op LEFT JOIN `user` u ON op.id=u.assign_operator_id LEFT JOIN `order` o ON (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
 where %s GROUP BY op.id,op.nickname,u.origin
'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for id,nickname,origin,countu,counto,sumo in rows:
        if not data.has_key(id):
            data[id] = {'nickname':nickname,
                              'countu':countu,
                              'counto':counto,
                              'sumo':sumo,
                              'items':[],

            }
        else:
            data[id]['countu'] = data[id]['countu']+countu
            data[id]['counto'] = data[id]['counto']+counto
            data[id]['sumo'] = data[id]['sumo']+sumo
        data[id]['items'].append({'origin':origin,'countu':countu,'counto':counto,'sumo':sumo})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['nickname'])

    #print dir(rows)
    return render_template('report/lqweihu_report_laiyuan.html',operators=operators,rows=_data)

@report.route('/lqweihu/dengji')
@admin_required
def lqweihu_report_dengji():
    operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'))
    _conditions = [r"""op.team like 'C%'"""]
    _conditions.append('`op`.`assign_user_type`>0')
    _conditions.append('`op`.`status`<>9')
    intent_level = request.args.get('intent_level','')
    if intent_level:
        _conditions.append('`u`.`intent_level`="%s"'%intent_level)    
    
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`u`.`assign_operator_id`=%s'%assign_operator_id)    
    
    

    _sql = '''SELECT op.id,op.nickname,u.intent_level,count(distinct u.user_id) as countu,count(o.order_id) as counto,IFNULL(sum(o.item_fee),0) as sumo from operator op LEFT JOIN `user` u ON op.id=u.assign_operator_id LEFT JOIN `order` o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
 where %s GROUP BY op.id,op.nickname,u.intent_level
'''%' AND '.join(_conditions)
    #return _sql
    rows = db.session.execute(_sql)
    data = OrderedDict()
    for id,nickname,intent_level,countu,counto,sumo in rows:
        if not data.has_key(id):
            data[id] = {'nickname':nickname,
                              'countu':countu,
                              'counto':counto,
                              'sumo':sumo,
                              'items':[],

            }
        else:
            data[id]['countu'] = data[id]['countu']+countu
            data[id]['counto'] = data[id]['counto']+counto
            data[id]['sumo'] = data[id]['sumo']+sumo
        data[id]['items'].append({'intent_level':intent_level,'countu':countu,'counto':counto,'sumo':sumo})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['nickname'])

    #print dir(rows)
    return render_template('report/lqweihu_report_dengji.html',operators=operators,rows=_data)
@report.route("/lqweihu/product")
@admin_required
def lqweihu_report_product():

    operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'))
    _conditions = [r"""op.team like 'C%'"""]
    _conditions.append('`op`.`assign_user_type`>0')
    _conditions.append('`op`.`status`<>9')
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`op`.`id`="%s"'%assign_operator_id)
        
    sql = '''SELECT op.id,op.nickname,sum(oi.fee) as allsale, count(o.order_id) as allorder,i.category_id as protype
		from operator as op LEFT JOIN `user` u ON u.assign_operator_id=op.id
			LEFT JOIN `order`o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
			LEFT JOIN order_item oi ON oi.order_id=o.order_id
			LEFT JOIN sku s ON s.id=oi.sku_id
			LEFT JOIN item i ON i.id=s.item_id
			WHERE %s GROUP BY op.id,protype'''%' AND '.join(_conditions)
    rows = db.session.execute(sql)
    data = OrderedDict()
    for id,nickname,allsale,allorder,protype in rows:
        if not data.has_key(id):
            data[id] = {'nickname':nickname,
                                      'protype':[],

            }
        sql2 = """select count(DISTINCT u.user_id) as usersc,count(o.order_id) as allorder,IFNULL(sum(o.item_fee),0) as allfee from operator as op LEFT JOIN `user` u ON u.assign_operator_id=op.id
			LEFT JOIN `order`o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2) where op.id="""+str(id)
        rows2 = db.session.execute(sql2)
        for usersc,allorder,allfee in rows2:
            data[id]['usersc'] = usersc
            data[id]['allorder'] = allorder
            data[id]['allfee'] = allfee
        if protype:
            data[id]['protype'].append({'protype':protype,'allsale':allsale})
    _data = data.values()
    _data = sorted(_data,key=lambda d:d['nickname'])
        
    return render_template('report/lqweihu_report_product.html', operators=operators, rows=_data)
   


@report.route("/lqweihu/cusAges")
@admin_required
def lqweihu_report_cusAges():
    operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'))
    _conditions = [r"""op.team like 'C%'"""]
    _conditions.append('`op`.`assign_user_type`>0')
    _conditions.append('`op`.`status`<>9')
    assign_operator_id = request.args.get('assign_operator_id','')
    ages = request.args.get('ages','')
    if assign_operator_id:
        _conditions.append('`u`.`assign_operator_id`="%s"'%assign_operator_id)
    if not ages:
        sql2 = '''
                sum(CASE WHEN u.ages<=20 THEN 1 ELSE 0 END) as age20, 
					sum(CASE WHEN u.ages>20 AND u.ages<=30 THEN 1 ELSE 0 END) as age30, 
					sum(CASE WHEN u.ages>30 AND u.ages<=40 THEN 1 ELSE 0 END) as age40, 
					sum(CASE WHEN u.ages>40 AND u.ages<=50 THEN 1 ELSE 0 END) as age50, 
					sum(CASE WHEN u.ages>50 THEN 1 ELSE 0 END) as age60
                '''
    if ages:
        if ages=='1':
            sql2 = '''
                sum(CASE WHEN u.ages<=20 THEN 1 ELSE 0 END) as age20, 
					sum(CASE WHEN u.ages>20 AND u.ages<=30 THEN 1 ELSE 0 END) as age30, 
					sum(CASE WHEN u.ages>30 AND u.ages<=40 THEN 1 ELSE 0 END) as age40, 
					sum(CASE WHEN u.ages>40 AND u.ages<=50 THEN 1 ELSE 0 END) as age50, 
					sum(CASE WHEN u.ages>50 THEN 1 ELSE 0 END) as age60
                '''
            age_condition = 1
        if ages=='2':
            sql2 = 'sum(CASE WHEN u.ages<=20 THEN 1 ELSE 0 END) as age20'
            age_condition = 2
        if ages=='3':
            sql2 = 'sum(CASE WHEN u.ages>20 AND u.ages<=30 THEN 1 ELSE 0 END) as age30'
            age_condition = 3
        if ages=='4':
            sql2 = 'sum(CASE WHEN u.ages>30 AND u.ages<=40 THEN 1 ELSE 0 END) as age40'
            age_condition = 4
        if ages=='5':
            sql2 = 'sum(CASE WHEN u.ages>40 AND u.ages<=50 THEN 1 ELSE 0 END) as age50'
            age_condition = 5
        if ages=='6':
            sql2 = 'sum(CASE WHEN u.ages>50 THEN 1 ELSE 0 END) as age60'
            age_condition = 6
        
    sql = '''SELECT op.id, op.nickname, count(distinct u.user_id) as coutu,%s                                  
            from operator as op
            LEFT JOIN `user` u ON op.id=u.assign_operator_id
            WHERE %s GROUP BY op.id, op.nickname'''%(sql2,' AND '.join(_conditions))
    rows = db.session.execute(sql)
    return render_template('report/lqweihu_report_cusAges.html', operators=operators,rows=rows)


# @report.route('/lqweihu/user_time')
# @admin_required
# def lqweihu_report_user_time():
#
#     operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'))
#     _conditions = [r"""op.team like 'C%'"""]
#     _conditions.append('`op`.`assign_user_type`>0')
#     _conditions.append('`op`.`status`<>9')
#     assign_operator_id = request.args.get('assign_operator_id','')
#     if assign_operator_id:
#         _conditions.append('`op`.`id`="%s"'%assign_operator_id)
#
#     sql='''SELECT op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(u.assign_time))/30) as usertime,ceil((TO_DAYS(now())-TO_DAYS(u.assign_time))/360) as usertime2,count(distinct u.user_id) as alluser,IFNULL(sum(o.item_fee),0) as allfee, count(o.order_id) as allorder
# 	FROM operator as op
# 	LEFT JOIN `user` u ON u.assign_operator_id=op.id
# 	LEFT JOIN `order` o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
#             WHERE %s GROUP BY op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(u.assign_time))/30),ceil((TO_DAYS(now())-TO_DAYS(u.assign_time))/360)''' %' AND '.join(_conditions)
#
#
#     rows = db.session.execute(sql)
#     data = OrderedDict()
#
#     for id,nickname,usertime,usertime2,alluser,allfee,allorder in rows:
#         if not data.has_key(id):
#             data[id] = {'nickname':nickname,
#                         'alluser':alluser,
#                         'allfee':allfee,
#                         'allorder':allorder,
#                         'items':[],
#                         'items2':[],
#                         'items3':[],
#             }
#         else:
#             data[id]['alluser'] = data[id]['alluser']+alluser
#             data[id]['allfee'] = data[id]['allfee']+allfee
#             data[id]['allorder'] = data[id]['allorder']+allorder
#
#         if usertime2>1:
#             data[id]['items2'].append({'alluser':alluser,'allfee':allfee,'allorder':allorder,'usertime':usertime})
#         else:
#             if usertime<=1:
#                 data[id]['items3'].append({'alluser':alluser,'allfee':allfee,'allorder':allorder,'usertime':usertime})
#             else:
#                 data[id]['items'].append({'alluser':alluser,'allfee':allfee,'allorder':allorder,'usertime':usertime})
#     _data = data.values()
#     _data = sorted(_data,key=lambda d:d['nickname'])
#     return render_template('report/lqweihu_report_user_time.html', operators=operators, rows=_data)


@report.route('/lqweihu/user_time')
@admin_required
def lqweihu_report_user_time():

    operators = Operator.query.filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'))
    # operators = Operator.query.join(User,User.user_id==Operator.id).join(Order,Order.user_id==User.user_id).join(User_Assign_Log,User_Assign_Log.user_id==User.user_id).filter(Operator.assign_user_type>0,Operator.status<>9,Operator.team.like('C%'),User_Assign_Log.one_two==1)
    _conditions = [r"""op.team like 'C%'"""]
    _conditions.append('`op`.`assign_user_type`>0')
    _conditions.append('`op`.`status`<>9')
    _conditions.append('ua.one_two=1')
    _conditions.append('o.created_by=op.id')
    assign_operator_id = request.args.get('assign_operator_id','')
    if assign_operator_id:
        _conditions.append('`op`.`id`="%s"'%assign_operator_id)

    sql1='''SELECT op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(ua.assign_time))/30) as usertime,ceil((TO_DAYS(now())-TO_DAYS(ua.assign_time))/360) as usertime2,count(distinct u.user_id) as alluser,IFNULL(sum(o.item_fee),0) as allfee, count(o.order_id) as allorder
        FROM operator as op
        LEFT JOIN `user` u ON u.assign_operator_id=op.id
        LEFT JOIN `order` o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
        LEFT JOIN user_assign_log ua ON ua.user_id=u.user_id
                WHERE %s GROUP BY op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(ua.assign_time))/30),ceil((TO_DAYS(now())-TO_DAYS(ua.assign_time))/360)''' %' AND '.join(_conditions)

    sql2='''SELECT ua.user_id,op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(o.created))/30) as usertime,ceil((TO_DAYS(now())-TO_DAYS(o.created))/360) as usertime2
            FROM operator as op
            LEFT JOIN `user` u ON u.assign_operator_id=op.id
			LEFT JOIN `order` o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
			LEFT JOIN user_assign_log ua ON ua.user_id=u.user_id
			WHERE %s GROUP BY op.nickname,ua.user_id,op.id,ceil((TO_DAYS(now())-TO_DAYS(o.created))/30),ceil((TO_DAYS(now())-TO_DAYS(o.created))/360) ''' % ' AND '.join(_conditions)

    rows1 = db.session.execute(sql1)
    rows2 = db.session.execute(sql2)
    data1 = OrderedDict()
    data2 = OrderedDict()
    data4 = defaultdict(list)

    for user_id,id,nickname,usertime,usertime2 in rows2:
        if not data2.has_key(id):
            data2[id]={'items4':[],
                       'items5':[],
                       'items6':[]
                       }
        if usertime2>1:
            data2[id]['items4'].append(int(user_id))
        else:
            if usertime<=1:
                data2[id]['items5'].append(user_id)
            else:
                data2[id]['items6'].append({'usertime': usertime, 'user_id': user_id})

    for i in data2.keys():
        data3 = defaultdict(list)
        for m in range(0,len(data2[i]['items6'])):
            usertime = data2[i]['items6'][m]['usertime']
            user_id = data2[i]['items6'][m]['user_id']
            data3[usertime].append(int(user_id))
        data4[i].append(data3)

    for id,nickname,usertime,usertime2,alluser,allfee,allorder in rows1:
        for keys in data4.keys():
            if keys==id:
                if not data1.has_key(id):
                    data1[id] = {'nickname':nickname,
                                'alluser':alluser,
                                'allfee':allfee,
                                'allorder':allorder,
                                'items':[],
                                'items2':[],
                                'items3':[],
                    }
                if usertime2>1:
                    if len(data2[keys]['items4'])==1:
                        sql4_user_in_usertime = '(' + str(tuple(data2[keys]['items4'])[0]) + ')'
                    else:
                        sql4_user_in_usertime = str(tuple(data2[keys]['items4']))

                    if len(data2[keys]['items4'])==0:
                        data1[id]['items2'].append({'alluser':0,'allfee':0,'allorder':0,'usertime':usertime})
                    else:
                         sql4='''SELECT op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(o.created))/30) as usertime,ceil((TO_DAYS(now())-TO_DAYS(o.created))/360) as usertime2,count(distinct u.user_id) as alluser,IFNULL(sum(o.item_fee),0) as allfee, count(o.order_id) as allorder
                                    FROM operator as op
                                    LEFT JOIN `user` u ON u.assign_operator_id=op.id
                                    LEFT JOIN `order` o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
                                    LEFT JOIN user_assign_log ua ON ua.user_id=u.user_id
                                    WHERE o.created_by=op.id and ua.one_two=1 and `op`.`status`<>9 and `op`.`assign_user_type`>0 and op.team like 'C%'
                                        and ceil((TO_DAYS(now())-TO_DAYS(o.created))/30)=1 and ua.user_id in ''' + sql4_user_in_usertime + '''
                                    GROUP BY op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(o.created))/30),ceil((TO_DAYS(now())-TO_DAYS(o.created))/360)'''
                         rows4 = db.session.execute(sql4)
                         for sql4_id,sql4_nickname,sql4_usertime,sql4_usertime2,sql4_alluser,sql4_allfee,sql4_allorder in rows4:
                             sql4_newallorder = sql4_allorder
                             sql4_newallfee = sql4_allfee
                             sql4_newalluser = sql4_alluser
                             data1[id]['items2'].append({'alluser':sql4_newalluser,'allfee':sql4_newallfee,'allorder':sql4_newallorder,'usertime':sql4_usertime})
                             data1[id]['alluser'] = data1[id]['alluser']+sql4_newalluser
                             data1[id]['allfee'] = data1[id]['allfee']+sql4_newallfee
                             data1[id]['allorder'] = data1[id]['allorder']+sql4_newallorder
                else:
                    if usertime<=1:
                        data1[id]['items3'].append({'alluser':alluser,'allfee':allfee,'allorder':allorder,'usertime':usertime})
                    else:
                        if len(data4[keys][0][usertime])==1:
                            user_in_usertime = '(' + str(tuple(data4[keys][0][usertime])[0]) + ')'
                        else:
                            user_in_usertime = str(tuple(data4[keys][0][usertime]))
                        # print user_in_usertime
                        if len(data4[keys][0][usertime])!=0:
                            sql3='''SELECT op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(o.created))/30) as usertime,ceil((TO_DAYS(now())-TO_DAYS(o.created))/360) as usertime2,count(distinct u.user_id) as alluser,IFNULL(sum(o.item_fee),0) as allfee, count(o.order_id) as allorder
                                    FROM operator as op
                                    LEFT JOIN `user` u ON u.assign_operator_id=op.id
                                    LEFT JOIN `order` o ON  (o.user_id=u.user_id AND `o`.`status` not in (1,103) and `o`.order_type=2)
                                    LEFT JOIN user_assign_log ua ON ua.user_id=u.user_id
                                    WHERE o.created_by=op.id and ua.one_two=1 and `op`.`status`<>9 and `op`.`assign_user_type`>0 and op.team like 'C%'
                                        and ceil((TO_DAYS(now())-TO_DAYS(o.created))/30)=1 and ua.user_id in''' + user_in_usertime + '''
                                    GROUP BY op.id,op.nickname,ceil((TO_DAYS(now())-TO_DAYS(o.created))/30),ceil((TO_DAYS(now())-TO_DAYS(o.created))/360)'''
                            rows3 = db.session.execute(sql3)
                            for  id,nickname,usertimes,usertime2,alluser,allfee,allorder in rows3:
                                newallorder = allorder
                                newallfee = allfee
                                newalluser = alluser
                            data1[id]['items'].append({'alluser':newalluser,'allfee':newallfee,'allorder':newallorder,'usertime':usertime})
                            data1[id]['alluser'] = data1[id]['alluser']+newalluser
                            data1[id]['allfee'] = data1[id]['allfee']+newallfee
                            data1[id]['allorder'] = data1[id]['allorder']+newallorder
                        else:
                            data1[id]['items'].append({'alluser':0,'allfee':0,'allorder':0,'usertime':usertime})
    _data1 = data1.values()
    _data1 = sorted(_data1,key=lambda d:d['nickname'])
    return render_template('report/lqweihu_report_user_time.html', operators=operators, rows1=_data1)


@report.route('/sale/waitStaffConfirm')
@admin_required
def sale_report_by_wait_staff_confirm():
    period = ''
    _conditions = ['`order`.status NOT IN (1,103)','`order`.status<200']#['`order`.status IN (2,3,40,4,5,6,60,100)']
 
    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`created`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`created`<="%s"'%_end_date)
        
    depart = request.args.get('depart','')
    if depart:
        _conditions.append('`order`.`team` LIKE "'+depart+'%"')

    if not _start_date and not _end_date:
        _conditions.append('`order`.`date`="%s"'%datetime.now().strftime('%y%m%d'))
        period = datetime.now().strftime('%Y-%m-%d')
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
`user`.origin,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
 SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums` FROM `order` 
 LEFT JOIN `operator` ON `order`.created_by = `operator`.id
 JOIN `user` ON `user`.user_id = `order`.user_id
WHERE %s
GROUP BY `user`.origin'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[1]
        total_fee += r[2]

    return render_template('report/sale_report_by_wait_staff_confirm.html',rows=_rows,total_fee=total_fee,total_orders=total_orders)

@report.route('/financial/delivery')
@admin_required
def financial_report_by_delivery():
    period = ''
    _conditions = []#['`order`.status IN (2,3,40,4,5,6,60,100)']

    if not current_user.is_admin and current_user.team:
        _conditions.append('`order`.`team` LIKE "'+current_user.team+'%"')

    _start_date = request.args.get('start_date','')
    if _start_date:
        _conditions.append('`order`.`delivery_time`>="%s"'%_start_date)

    _end_date = request.args.get('end_date','')
    if _end_date:
        _conditions.append('`order`.`delivery_time`<="%s"'%_end_date)
    
    depart = request.args.get('depart','')
    if depart:
        _conditions.append('`order`.`team` LIKE "'+depart+'%"')
    
    
    if not _start_date and not _end_date:
        _conditions.append('`order`.`date`="%s"'%datetime.now().strftime('%y%m%d'))
        period = datetime.now().strftime('%Y-%m-%d')
    else:
        period = '%s ~ %s'%(_start_date if _start_date else u'开始',_end_date if _end_date else u'现在')

    _sql = '''SELECT
`user`.origin,COUNT(`order`.order_id) AS `order_nums`,SUM(`order`.item_fee-`order`.discount_fee) AS `total_fee`,
 SUM(CASE WHEN `order`.item_fee<=`order`.discount_fee THEN 1 ELSE 0 END) AS `zero_order_nums` FROM `order`
 LEFT JOIN `operator` ON `order`.created_by = `operator`.id
 JOIN `user` ON `user`.user_id = `order`.user_id
WHERE %s
GROUP BY `user`.origin'''%' AND '.join(_conditions)
    rows = db.session.execute(_sql)
    total_orders = 0
    total_fee = 0
    _rows = []
    for r in rows:
        _rows.append(r)
        total_orders += r[1]
        total_fee += r[2]

    return render_template('report/financial_report_by_delivery.html',rows=_rows,total_fee=total_fee,total_orders=total_orders)
