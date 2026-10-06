CREATE TABLE users (id BIGSERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, name VARCHAR(120) NOT NULL, role VARCHAR(20) NOT NULL CHECK(role IN ('ADMIN','LIBRARIAN','MEMBER')), is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX users_email_idx ON users(email);
CREATE TABLE auth_sessions (id VARCHAR(36) PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX auth_sessions_user_idx ON auth_sessions(user_id);
CREATE TABLE books (id BIGSERIAL PRIMARY KEY, isbn VARCHAR(20) NOT NULL UNIQUE, title VARCHAR(200) NOT NULL, author VARCHAR(160) NOT NULL, description TEXT, total_copies INTEGER NOT NULL CHECK(total_copies >= 0), available_copies INTEGER NOT NULL CHECK(available_copies >= 0 AND available_copies <= total_copies), is_active BOOLEAN NOT NULL DEFAULT TRUE, created_by BIGINT NOT NULL REFERENCES users(id), updated_by BIGINT NOT NULL REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE INDEX books_title_idx ON books(title);
CREATE INDEX books_author_idx ON books(author);
CREATE TABLE loans (id BIGSERIAL PRIMARY KEY, member_id BIGINT NOT NULL REFERENCES users(id), book_id BIGINT NOT NULL REFERENCES books(id), borrowed_at TIMESTAMPTZ NOT NULL, due_at TIMESTAMPTZ NOT NULL, returned_at TIMESTAMPTZ, processed_by BIGINT REFERENCES users(id), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), CHECK(due_at > borrowed_at));
CREATE INDEX loans_member_idx ON loans(member_id);
CREATE INDEX loans_due_idx ON loans(due_at);
CREATE UNIQUE INDEX loans_one_active_copy_idx ON loans(member_id, book_id) WHERE returned_at IS NULL;
CREATE TABLE activity_logs (id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL REFERENCES users(id), action VARCHAR(60) NOT NULL, entity_type VARCHAR(40) NOT NULL, entity_id BIGINT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());

