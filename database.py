import psycopg2


def create_connection() -> None:
    try:
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            database="proxyapi",
            user="postgres",
            password="12345",
            client_encoding='UTF-8'
        )
        print('База данных подключена, можно работать!')
        return connection
    except Exception as e:
        print(f'База даннах не подключена. Ошибка:\n{e}')


def setup_database() -> None:
    conn = create_connection()
    with conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    thread_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)''')
        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS users (
                           id SERIAL PRIMARY KEY,
                           user_telegram_id BIGINT UNIQUE,
                           telegram_username TEXT,
                           balance INTEGER DEFAULT 0,
                           is_active BOOLEAN DEFAULT FALSE
                       )
        ''')


def add_member_to_db(user_telegram_id: int, telegram_username: str) -> None:
    conn = create_connection()
    try:
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT id FROM users WHERE user_telegram_id = %s
                       ''', (user_telegram_id,))
        user = cursor.fetchone()

        if not user:
            cursor.execute('''
                           INSERT INTO users (
                               user_telegram_id,
                               telegram_username
                           ) VALUES (%s, %s)
                           ''', (
                               user_telegram_id,
                               telegram_username,
                            ))
            conn.commit()
            print("Пользователь успешно добавлен.")

    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        cursor.close()
        conn.close()


def take_users() -> str:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY id")
        rows = cursor.fetchall()
        if rows:
            response = ''
            for user in rows:
                response += f'{user[0]}. id: {user[1]}, username: @{user[2]}\n'
        else:
            response = 'Пока нет зарегистрированных пользователей'

    return response


def set_user_active_status(user_id: int, is_active: bool) -> None:
    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET is_active = %s
            WHERE user_telegram_id = %s
        ''', (is_active, user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def is_user_active(user_id: int) -> bool:
    conn = create_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_active
            FROM users
            WHERE user_telegram_id = %s
        ''', (user_id,))
        return cursor.fetchone()[0]
    except Exception:
        return False
    finally:
        cursor.close()
        conn.close()


def get_thread_id(user_id: int) -> str:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT thread_id FROM messages WHERE user_id = %s
                   """, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else None


def save_message(user_id: int, thread_id: str, role: str, content: str):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO messages (user_id, thread_id, role, content) VALUES (%s, %s, %s, %s)",
            (user_id, thread_id, role, content)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка при сохранении в БД: {e}")


def take_messages() -> str:
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        if rows:
            response = ''
            for user in rows:
                response += f'id: {user[1]}\nВремя: {user[5]}\nСообщение:\n{user[4]}\n\n'
        else:
            response = 'Пока никто ничего не спрашивал...'

    return response


def delete_user_history(user_id: int) -> bool:
    conn = create_connection()
    cursor = conn.cursor()
    try:
        print('Попали в delete_user_history')
        cursor.execute(
            "DELETE FROM messages WHERE user_id = %s", (user_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        print('История удалена')
        return True
    except Exception:
        print('История не удалена')
        return False


def take_user_telegram_id() -> list[tuple]:
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_telegram_id FROM users")
            return cursor.fetchall()
    except Exception as e:
        print(e)
    finally:
        if conn:
            conn.close()


def delete_invalid_user(chat_id: int):
    """Удаляет невалидного пользователя из БД"""
    conn = create_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM users WHERE user_telegram_id = %s",
                (chat_id,)
            )
            conn.commit()
    except Exception as e:
        print(e)
    finally:
        if conn:
            conn.close()
