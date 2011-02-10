# -*- coding: utf-8 -*-

import sys, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from withings import WithingsAccount
from withings import WithingsAPIError
from fit import FitEncoder_Weight

from flask import Flask
from flask import request
from flask import url_for
from flask import render_template
from flask import send_file
app = Flask(__name__)


class GenerateError(Exception):
    pass


@app.route('/', methods=['GET', 'POST'])
def index():
    error = ''
    if request.method == 'POST':
        try:
            fp = generate(request)
            return send_file(fp, attachment_filename='weight.fit', as_attachment=True)
        except GenerateError, e:
            error = e
        except Exception, e:
            error = 'An unknown error occured'
    return render_template('index.html', error=error)


def generate(request):
    username = request.form.get('username')
    password = request.form.get('password')
    shortname = request.form.get('shortname')

    try:
        withings = WithingsAccount(username, password)
        user = withings.get_user_by_shortname(shortname)
    except WithingsAPIError, e:
        if e.status == 264:
            raise GenerateError('invalid username or password')
        raise
    if not user:
        raise GenerateError('could not find user: %s' % shortname)
    if not user.ispublic:
        raise GenerateError('user %s has not opened withings data' % shortname)

    startdate = strtotimestamp(request.form.get('startdate'))
    enddate = strtotimestamp(request.form.get('enddate'))
    groups = user.get_measure_groups(startdate=startdate, enddate=enddate)
    if len(groups) == 0:
        raise GenerateError('no weight scale data is available')

    fit = FitEncoder_Weight()
    fit.write_file_info()
    fit.write_file_creator()

    for group in groups:
        dt = group.get_datetime()
        weight = group.get_weight()
        fat_ratio = group.get_fat_ratio()
        fit.write_device_info(timestamp=dt)
        fit.write_weight_scale(timestamp=dt, weight=weight, percent_fat=fat_ratio)
    fit.finish()
    return fit.buf

def strtotimestamp(s):
    try:
        import time
        ts = time.strptime(s, '%Y-%m-%d')
        return int(time.mktime(ts))
    except:
        return None


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

