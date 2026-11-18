from flask import Blueprint
from app.web import api,page
bp=Blueprint('m3b_handovers',__name__)
@bp.get('/m3b_handovers')
def screen():return page(4,'m3b_handovers.html')
@bp.route('/api/m3b_handovers',methods=['GET','POST'])
def preview():return api(4)
