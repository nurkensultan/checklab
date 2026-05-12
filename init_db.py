"""
init_db.py - Скрипт для инициализации базы данных SaaS версии
"""
from database import init_database, create_demo_data

if __name__ == '__main__':
    print("=" * 60)
    print("Инициализация CheckLab Engine SaaS")
    print("=" * 60)
    
    init_database()
    create_demo_data()
    
    print("=" * 60)
    print("Готово! Запустите приложение командой: python app.py")
    print("=" * 60)
