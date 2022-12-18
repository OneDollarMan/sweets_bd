from datetime import time

from mysql.connector import connect, Error


# Класс репозитория, общающийся с БД
class Repo:
    ROLE_STOREKEEPER = 1  # Переменные ролей
    ROLE_ADMINISTRATOR = 2

    def __init__(self, host, user, password, db, port):
        self.connection = None
        self.cursor = None
        self.connect_to_db(host, user, password, db, port)
        if self.connection is not None and self.cursor is not None:
            self.select_db(db)
            self.get_tables = lambda: self.raw_query("SHOW TABLES")

            # Запросы к пользователям
            self.get_user = lambda username: self.get_query(
                f"SELECT * FROM user WHERE username='{username}'")
            self.get_all_users = lambda: self.raw_query(
                "SELECT user.id, username, fio, role.name FROM user JOIN role ON user.role_id=role.id WHERE hidden='0' ORDER BY user.id")
            self.login_user = lambda username, password: self.get_query(
                f"SELECT * FROM user WHERE username='{username}' AND password='{password}' AND hidden='0'")
            self.add_u = lambda params: self.write_query(
                "INSERT INTO user SET fio=%(fio)s, username=%(username)s, password=%(password)s, role_id=%(role_id)s",
                params)
            self.rm_user = lambda id: self.write_query(f"DELETE FROM user WHERE id='{id}'")
            self.select_users = lambda: self.raw_query("SELECT id, fio FROM user WHERE role_id='1' AND hidden='0'")
            self.hide_user = lambda id: self.write_query(f"UPDATE user SET hidden='1' WHERE id='{id}'")
            self.get_user_by_id = lambda id: self.get_query(
                f"SELECT user.id, username, fio, role.name FROM user JOIN role ON user.role_id=role.id WHERE hidden='0' AND user.id='{id}'")

            # Запросы к ролям
            self.get_roles = lambda: self.raw_query("SELECT * from role")

            # Запросы к клиентам
            self.get_clients = lambda: self.raw_query("SELECT * FROM client WHERE hidden='0'")
            self.add_client = lambda params: self.write_query(f"INSERT INTO client SET fio=%(fio)s, phone=%(phone)s", params)
            self.select_clients = lambda: self.raw_query("SELECT id, fio FROM client WHERE hidden='0'")
            self.hide_client = lambda id: self.write_query(f"UPDATE client SET hidden='1' WHERE id='{id}'")
            self.get_client_by_fio_phone = lambda fio, phone: self.get_query(f"SELECT * FROM client WHERE fio='{fio}' AND phone='{phone}'")
            self.select_clients_all = lambda: self.raw_query("SELECT id, fio FROM client")

            # Запросы к поставщикам
            self.get_suppliers = lambda: self.raw_query("SELECT * FROM supplier WHERE hidden='0'")
            self.add_supplier = lambda params: self.write_query(f"INSERT INTO supplier SET name=%(name)s, address=%(address)s, phone=%(phone)s", params)
            self.select_suppliers = lambda: self.raw_query("SELECT id, name FROM supplier WHERE hidden='0'")
            self.hide_supplier = lambda id: self.write_query(f"UPDATE supplier SET hidden='1' WHERE id='{id}'")
            self.get_supplier_by_name_address = lambda name, address: self.get_query(f"SELECT * FROM supplier WHERE name='{name}' AND address='{address}'")

            # Запросы к компонентам
            self.get_components = lambda: self.raw_query("SELECT c.id, s.name, c.name, amount FROM component c JOIN supplier s ON c.supplier_id=s.id WHERE (s.hidden='0' OR c.amount > 1) AND c.hidden='0'")
            self.select_components = lambda: self.raw_query("SELECT id, name FROM component WHERE hidden='0'")
            self.add_component = lambda params: self.write_query("INSERT INTO component SET name=%(name)s, amount=0, supplier_id=%(supplier_id)s", params)
            self.get_component_by_name_supplier = lambda name, supplier_id: self.raw_query(f"SELECT * FROM component WHERE name='{name}' AND supplier_id='{supplier_id}' AND hidden='0'")
            self.add_component_amount = lambda params: self.write_query("UPDATE component SET amount=amount+%(amount)s WHERE id=%(component_id)s", params)
            self.hide_component = lambda id: self.write_query(f"UPDATE component SET hidden=1 WHERE id='{id}'")
            self.change_component_amount = lambda id, amount: self.write_query(f"UPDATE component SET amount=amount+'{amount}' WHERE id='{id}'")

            # Запросы к продуктам
            self.get_sweets = lambda: self.raw_query("SELECT id, name, price FROM sweet WHERE hidden='0'")
            self.get_sweet_by_name = lambda name: self.raw_query(f"SELECT * FROM sweet WHERE name='{name}' AND hidden='0'")
            self.add_sweet = lambda params: self.write_query("INSERT INTO sweet SET name=%(name)s, price=%(price)s", params)
            self.hide_sweet = lambda id: self.write_query(f"UPDATE sweet SET hidden=1 WHERE id='{id}'")
            self.get_sweet = lambda id: self.get_query(f"SELECT * FROM sweet WHERE id='{id}'")
            self.select_sweets = lambda: self.raw_query("SELECT id, name FROM sweet WHERE hidden='0'")

            # Запросы к компонентам в продукте
            self.get_components_of_sweet = lambda id: self.raw_query(f"SELECT c.id, c.name, sc.amount FROM sweet_has_component sc JOIN component c ON sc.component_id=c.id WHERE sweet_id='{id}'")
            self.remove_component_from_sweet = lambda sweet_id, component_id: self.write_query(f"DELETE FROM sweet_has_component WHERE sweet_id='{sweet_id}' AND component_id='{component_id}'")
            self.get_component_from_sweet = lambda sweet_id, component_id: self.get_query(f"SELECT * FROM sweet_has_component WHERE sweet_id='{sweet_id}' AND component_id='{component_id}'")
            self.add_component_to_sweet = lambda params: self.write_query("INSERT INTO sweet_has_component SET sweet_id=%(sweet_id)s, component_id=%(component_id)s, amount=%(amount)s", params)
            self.update_component_to_sweet = lambda params: self.write_query("UPDATE sweet_has_component SET amount=%(amount)s WHERE sweet_id=%(sweet_id)s AND component_id=%(component_id)s", params)
            self.get_amounts = lambda sweet_id: self.raw_query(f"SELECT c.id, sc.amount, c.amount FROM sweet_has_component sc JOIN component c ON sc.component_id=c.id WHERE sweet_id='{sweet_id}'")

            # Запросы к заказам
            self.get_orders = lambda: self.raw_query("SELECT o.id, date, c.fio FROM sweets.order o JOIN client c ON o.client_id=c.id ORDER BY date")
            self.add_order = lambda params: self.write_query(f"INSERT INTO sweets.order SET date=%(date)s, client_id=%(client_id)s, user_id=%(user_id)s", params)
            self.get_order = lambda id: self.get_query(f"SELECT o.id, date, c.fio, (SELECT ROUND(SUM(amount*price),1) FROM order_has_sweet os JOIN sweet s ON os.sweet_id=s.id WHERE order_id='{id}') FROM sweets.order o JOIN client c ON o.client_id=c.id WHERE o.id='{id}'")
            self.rm_order = lambda id: self.write_query(f"DELETE FROM sweets.order WHERE id='{id}'")

            # Запросы к продуктам в заказе
            self.get_order_sweets = lambda id: self.raw_query(f"SELECT s.id, name, price, amount FROM order_has_sweet os JOIN sweet s ON os.sweet_id=s.id WHERE order_id='{id}'")
            self.add_sweet_to_order = lambda params: self.write_query("INSERT INTO order_has_sweet SET order_id=%(order_id)s, sweet_id=%(sweet_id)s, amount=%(amount)s", params)
            self.get_sweet_from_order = lambda order_id, sweet_id: self.get_query(f"SELECT * FROM order_has_sweet WHERE order_id='{order_id}' AND sweet_id='{sweet_id}'")
            self.update_sweet_to_order = lambda params: self.write_query("UPDATE order_has_sweet SET amount=amount+%(amount)s WHERE order_id=%(order_id)s AND sweet_id=%(sweet_id)s", params)
            self.rm_sweet_from_order = lambda order_id, sweet_id: self.write_query(f"DELETE FROM order_has_sweet WHERE order_id='{order_id}' AND sweet_id='{sweet_id}'")

            # Статистика
            self.get_stat_sums = lambda: self.raw_query("SELECT o.id, DATE_FORMAT(o.date, '%e-%m-%Y'), ROUND(SUM(amount*price),1) FROM order_has_sweet os JOIN sweet s, sweets.order o WHERE os.sweet_id=s.id AND os.order_id=o.id GROUP BY YEAR(o.date), MONTH(o.date), DAY(o.date)")
            self.get_stat_components = lambda: self.raw_query("SELECT component_id, c.name, SUM(cs.amount*sweet_amount) FROM sweet_has_component cs JOIN (SELECT sweet_id, SUM(amount) sweet_amount FROM order_has_sweet os JOIN sweets.order o ON os.order_id=o.id WHERE DATE(o.date)=DATE(NOW()) GROUP BY sweet_id) all_sweets, component c WHERE cs.sweet_id=all_sweets.sweet_id AND cs.component_id=c.id GROUP BY component_id;")

    def connect_to_db(self, host, user, password, db, port):  # Функция подключения к БД
        try:
            self.connection = connect(host=host, user=user, password=password, port=port)
            self.cursor = self.connection.cursor()
            self.cursor.execute("SHOW DATABASES")
            for res in self.cursor:
                if res[0] == db:
                    self.cursor.fetchall()
                    return
            for line in open('dump.sql'):
                self.cursor.execute(line)
            self.connection.commit()
            print('dump loaded successfully')
        except Error as e:
            print(e)

    def select_db(self, db):
        self.cursor.execute(f"USE {db}")

    def raw_query(self, query, params=None):  # Функция, отправляющая запрос к БД
        if self.cursor and query:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            return self.cursor.fetchall()

    def write_query(self, query, params=None):  # Тоже
        if self.cursor and query:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            self.connection.commit()
            return self.cursor.fetchall()

    def get_query(self, query):  # Тоже
        if self.cursor and query:
            self.cursor.execute(query)
            return self.cursor.fetchone()

    def get_one_query(self, query):  # Тоже
        if self.cursor and query:
            self.cursor.execute(query)
            return self.cursor.fetchone()[0]

    def add_user(self, params):  # Добавление юзера с проверкой
        if not self.get_user(params['username']):
            self.add_u(params)
            return True
        else:
            return False

    def add_client_check(self, params):  # Добавление клиента с проверкой
        if not self.get_client_by_fio_phone(params['fio'], params['phone']):
            self.add_client(params)
            return True
        return False

    def add_supplier_check(self, params):  # Добавление поставщика с проверкой
        if not self.get_supplier_by_name_address(params['name'], params['address']):
            self.add_supplier(params)
            return True
        return False

    def add_component_check(self, params):  # Добавление одежды с проверкой
        if not self.get_component_by_name_supplier(params['name'], params['supplier_id']):
            self.add_component(params)
            return True
        return False

    def add_sweet_check(self, params):  # Добавление продукта с проверкой
        if not self.get_sweet_by_name(params['name']):
            self.add_sweet(params)
            return True
        return False

    def add_component_to_sweet_check(self, params):
        sc = self.get_component_from_sweet(params['sweet_id'], params['component_id'])
        if sc is None:
            self.add_component_to_sweet(params)
        else:
            self.update_component_to_sweet(params)

    def add_sweet_to_order_check(self, params):
        amounts = self.get_amounts(params['sweet_id'])
        for a in amounts:
            if a[1] * float(params['amount']) > a[2]:
                return False
        if self.get_sweet_from_order(params['order_id'], params['sweet_id']) is None:
            self.add_sweet_to_order(params)
        else:
            self.update_sweet_to_order(params)
        for a in amounts:
            self.change_component_amount(a[0], -(a[1] * float(params['amount'])))
        return True

    def get_orders_sorted(self, data):  # Вывод отфильтрованных счетов
        q = "SELECT o.id, date, c.fio FROM sweets.order o JOIN client c ON o.client_id=c.id"
        if data['client_id']:
            q = q + f" AND o.client_id='{data['client_id']}'"
        if data['date1']:
            q = q + f" AND date >= '{data['date1']}'"
        if data['date2']:
            q = q + f" AND date <= '{data['date2']}'"
        q = q + ' ORDER BY date'
        return self.raw_query(q)

    def remove_sweet_from_order(self, order_id, sweet_id):
        amounts = self.get_amounts(sweet_id)
        amount = self.get_sweet_from_order(order_id, sweet_id)
        for a in amounts:
            self.change_component_amount(a[0], +(a[1] * float(amount[2])))
        self.rm_sweet_from_order(order_id, sweet_id)

    def remove_order(self, id):
        sweets = self.get_order_sweets(id)
        for s in sweets:
            self.remove_sweet_from_order(id, s[0])
        self.rm_order(id)