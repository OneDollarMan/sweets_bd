import hashlib

from flask import url_for, render_template, request, redirect, send_from_directory, flash, session
from __init__ import app
import forms
from repo import *

# Создание объекта репозитория
repo = Repo(host=app.config['HOST'], user=app.config['USER'], password=app.config['PASSWORD'], db=app.config['DB'], port=app.config['PORT'])


def flash_errors(form):  # Вывод ошибок форм
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'warning')


@app.route("/")  # Главная страница
def index():
    if not session.get('loggedin'):
        return redirect(url_for('login'))
    return render_template('index.html', title="Главная", stat1=repo.get_stat_sums(), stat2=repo.get_stat_components())


@app.route("/login", methods=['GET', 'POST'])  # Страница авторизации
def login():
    if session.get('loggedin'):
        return redirect(url_for('index'))
    form = forms.LoginForm()
    if form.validate_on_submit():
        user = repo.login_user(form.login.data, hashlib.md5(form.password.data.encode('utf-8')).hexdigest())
        if user:
            flash('Вы авторизовались!', 'info')
            session['loggedin'] = True
            session['id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[4]
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль!', 'warning')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')  # Страница логаута
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))


@app.route("/users", methods=['GET', 'POST'])  # Страница пользователей
def users():
    form = forms.UserForm()
    form.role_id.choices = repo.get_roles()
    if form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            data = form.data
            data['password'] = hashlib.md5(data['password'].encode('utf-8')).hexdigest()
            if not repo.add_user(data):
                flash('Пользователь уже существует', 'warning')
            else:
                app.logger.warning(f'User {form.username.data} with role id {form.role_id.data} was added by {session.get("username")}')
            return redirect(url_for('users'))
    return render_template('users.html', title='Пользователи', us=repo.get_all_users(), form=form)


@app.route("/users/rm/<int:id>")  # Страница удаления пользователя
def rm_user(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.hide_user(id)
    return redirect(url_for('users'))


@app.route("/clients", methods=['GET', 'POST'])  # Страница клиентов
def clients():
    form = forms.ClientForm()
    if form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            if not repo.add_client_check(form.data):
                flash('Клиент уже существует', 'warning')
            else:
                app.logger.warning(f'New client was added by {session.get("username")}')
            return redirect(url_for('clients'))
    return render_template('clients.html', title="Клиенты", clients=repo.get_clients(), form=form)


@app.route("/clients/rm/<int:id>")  # Страница удаления клиента
def rm_clients(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.hide_client(id)
    return redirect(url_for("clients"))


@app.route("/suppliers", methods=['GET', 'POST'])  # Страница поставщиков
def suppliers():
    form = forms.SupplierForm()
    if form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            if not repo.add_supplier_check(form.data):
                flash('Поставщик уже существует', 'warning')
            else:
                app.logger.warning(f'New supplier was added by {session.get("username")}')
            return redirect(url_for('suppliers'))

    return render_template('suppliers.html', title="Поставщики", suppliers=repo.get_suppliers(), form=form)


@app.route("/suppliers/rm/<int:id>")  # Страница удаления поставщика
def rm_supplier(id):
    if session.get('role') >= repo.ROLE_ADMINISTRATOR:
        if id:
            repo.hide_supplier(id)
    return redirect(url_for("suppliers"))


@app.route("/components", methods=['GET', 'POST'])  # Страница компонентов
def components():
    form = forms.ComponentForm()
    form.supplier_id.choices = repo.select_suppliers()

    add_form = forms.AddForm()
    add_form.component_id.choices = repo.select_components()

    if form.validate_on_submit():
        if session.get('role') == repo.ROLE_ADMINISTRATOR:
            if not repo.add_component_check(form.data):
                flash('Данный товар у данного поставщика уже существует', 'warning')
                return redirect(url_for('wear'))
            app.logger.warning(f'new component was added by {session.get("username")}')
            return redirect(url_for('components'))

    return render_template('components.html', title="Компоненты", components=repo.get_components(), form=form, add_form=add_form)


@app.route("/components/add_amount", methods=['POST'])  # Страница добавления остатка компонента
def add_component():
    add_form = forms.AddForm()
    add_form.component_id.choices = repo.select_components()
    if session.get('role') >= repo.ROLE_STOREKEEPER:
        if add_form.validate_on_submit():
            repo.add_component_amount(add_form.data)
            flash('Количество товара добавлено', 'info')
    return redirect(url_for("components"))


@app.route("/components/rm/<int:id>")  # Страница удаления компонента
def rm_component(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.hide_component(id)
    return redirect(url_for("components"))


@app.route('/sweets', methods=['GET', 'POST'])  # Страница счетов
def sweets():
    form = forms.SweetForm()
    if form.validate_on_submit():
        if not repo.add_sweet_check(form.data):
            flash('Продукт уже существует', 'warning')
        else:
            app.logger.warning(f'New sweet was added by {session.get("username")}')
        return redirect(url_for('sweets'))
    return render_template('sweets.html', title='Продукция', sweets=repo.get_sweets(), form=form)


@app.route('/sweets/<int:id>', methods=['GET', 'POST'])  # Страница конкретного счета
def sweet(id):
    if session.get('role') >= repo.ROLE_ADMINISTRATOR:
        form = forms.AddForm()
        form.component_id.choices = repo.select_components()

        if form.validate_on_submit():
            data = form.data
            data['sweet_id'] = id
            repo.add_component_to_sweet_check(data)
            return redirect(url_for('sweet', id=id))
        return render_template('sweet.html', title='Продукт', sweet=repo.get_sweet(id), components=repo.get_components_of_sweet(id), form=form)
    else:
        flash('Нет доступа', 'warning')
        return redirect(url_for('sweets'))


@app.route('/sweets/<int:id>/rm/<int:component_id>', methods=['GET'])  # Страница удаления одежды из счета
def rm_component_from_sweets(id, component_id):
    repo.remove_component_from_sweet(id, component_id)
    flash('Компонент удален из состава', 'info')
    return redirect(url_for('sweet', id=id))


@app.route("/sweets/rm/<int:id>")  # Страница удаления продукта
def rm_sweet(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        if id:
            repo.hide_sweet(id)
    return redirect(url_for("sweets"))


@app.route('/orders', methods=['GET', 'POST'])
def orders():
    form = forms.OrderForm()
    form.client_id.choices = repo.select_clients()

    filter_form = forms.OrderFilterForm()
    filter_form.client_id.choices = [("", "---")] + repo.select_clients_all()

    if filter_form.validate_on_submit():
        return render_template('orders.html', title='Заказы', orders=repo.get_orders_sorted(filter_form.data), form=form, filter_form=filter_form)
    return render_template('orders.html', title='Заказы', orders=repo.get_orders(), form=form, filter_form=filter_form)


@app.route('/orders/add', methods=['POST'])
def add_order():
    form = forms.OrderForm()
    form.client_id.choices = repo.select_clients()
    if form.validate_on_submit():
        data = form.data
        data['user_id'] = session.get('id')
        repo.add_order(data)
        app.logger.warning(f'New order was added by {session.get("username")}')
    else:
        flash_errors(form)
    return redirect(url_for('orders'))


@app.route('/orders/<int:id>', methods=['GET', 'POST'])
def order(id):
    form = forms.OrderSweetForm()
    form.sweet_id.choices = repo.select_sweets()

    if form.validate_on_submit():
        data = form.data
        data['order_id'] = id
        if not repo.add_sweet_to_order_check(data):
            flash('Недостаточно компонентов для производства', 'warning')
    return render_template('order.html', title='Заказ', order=repo.get_order(id), sweets=repo.get_order_sweets(id), form=form)


@app.route('/orders/<int:id>/rm/<int:sweet_id>')
def rm_sweet_from_order(id, sweet_id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        repo.remove_sweet_from_order(id, sweet_id)
    else:
        flash('Недостаточно прав')
    return redirect(url_for('order', id=id))


@app.route('/orders/rm/<int:id>')
def rm_order(id):
    if session.get('role') == repo.ROLE_ADMINISTRATOR:
        repo.remove_order(id)
    else:
        flash('Недостаточно прав')
    return redirect(url_for('orders'))


# Вывод статических ресурсов
@app.route('/robots.txt')
@app.route('/sitemap.xml')
@app.route('/favicon.ico')
@app.route('/style.css')
@app.route('/script.js')
@app.route('/bus.jpg')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


# Обработка ошибки 404
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404
