from flask import Blueprint
from app.web import api,page
bp=Blueprint('m6_reconcile',__name__)
@bp.get('/m6_reconcile')
def screen():return page(7,'m6_reconcile.html')
@bp.route('/api/m6_reconcile',methods=['GET','POST'])
def preview():return api(7)
