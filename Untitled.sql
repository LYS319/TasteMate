use tastemate;
drop table comments;
drop table posts;
drop table users;

SET SQL_SAFE_UPDATES = 0;
UPDATE posts SET category = UPPER(category);
SET SQL_SAFE_UPDATES = 1;

ALTER TABLE posts ADD COLUMN is_notice INT DEFAULT 0;


UPDATE users SET is_admin = 1 WHERE email = 'zestoper@naver.com';

ALTER TABLE posts ADD COLUMN image_url VARCHAR(255) NULL;


CREATE TABLE likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    post_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);


-- 1️⃣ 데이터베이스 생성
CREATE DATABASE IF NOT EXISTS tastemate CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE tastemate;

-- 2️⃣ users 테이블 생성
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    is_admin INT DEFAULT 0,
    status VARCHAR(50) DEFAULT '정상'
);

-- 3️⃣ posts 테이블 생성
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(50),
    title VARCHAR(255),
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4️⃣ comments 테이블 생성
CREATE TABLE IF NOT EXISTS comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_id INT,
    post_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);


desc users;
insert into users(email,hashed_password,nickname,is_admin)
values('a','a','a',0);

select * from users;
commit;