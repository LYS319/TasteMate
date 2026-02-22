from Database import User, SessionLocal
from sqlalchemy.exc import IntegrityError

def create_super_admin():
    db = SessionLocal()
    try:
        admin = User(
            email="admin@example.com",
            hashed_password="adminpw",  # 실제 서비스에서는 반드시 해시된 비밀번호 사용!
            nickname="최고관리자",
            is_admin=1,
            status="정상"
        )
        db.add(admin)
        db.commit()
        print("최고관리자 계정이 생성되었습니다.")
    except IntegrityError:
        print("이미 해당 이메일의 계정이 존재합니다.")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
