-- Database schema for multi-university data platform
-- Designed to be flexible and extensible for different universities

-- Universities table to manage multiple institutions
CREATE TABLE universities (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL, -- e.g., 'ualberta', 'ubc', 'utoronto'
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    region VARCHAR(100),
    website_url TEXT,
    api_config JSONB, -- University-specific scraping configuration
    metadata JSONB, -- Flexible data for university-specific info
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Faculties/Schools - organized by university
CREATE TABLE faculties (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL, -- Faculty code (e.g., 'AR', 'EN')
    name VARCHAR(255) NOT NULL,
    website_url TEXT,
    dean_info JSONB, -- Dean name, contact, etc.
    metadata JSONB, -- University-specific faculty data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(university_id, code)
);

-- Subjects/Departments within faculties
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL, -- Subject code (e.g., 'CMPUT', 'MATH')
    name VARCHAR(255) NOT NULL,
    description TEXT,
    website_url TEXT,
    faculty_associations JSONB, -- Array of faculty codes this subject belongs to
    metadata JSONB, -- University-specific subject data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(university_id, code)
);

-- Courses - core academic offerings
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL, -- Full course code (e.g., 'CMPUT401')
    name VARCHAR(500) NOT NULL,
    description TEXT,
    credit_hours DECIMAL(3,1),
    level VARCHAR(20), -- 'undergraduate', 'graduate', 'junior', 'senior'
    prerequisites TEXT,
    corequisites TEXT,
    exclusions TEXT,
    website_url TEXT,
    fees JSONB, -- Fee information, can vary by university
    schedule_info JSONB, -- Lecture/lab/seminar hours
    metadata JSONB, -- University-specific course data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(university_id, code)
);

-- Terms/Semesters - flexible term system
CREATE TABLE terms (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL, -- e.g., 'Winter2025', 'Fall2024'
    name VARCHAR(100) NOT NULL,
    start_date DATE,
    end_date DATE,
    registration_start DATE,
    registration_end DATE,
    is_active BOOLEAN DEFAULT FALSE,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(university_id, code)
);

-- Course sections/offerings for specific terms
CREATE TABLE course_sections (
    id SERIAL PRIMARY KEY,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    term_id INTEGER REFERENCES terms(id) ON DELETE CASCADE,
    section_code VARCHAR(50) NOT NULL, -- e.g., 'LEC01', 'LAB02'
    section_type VARCHAR(50), -- 'lecture', 'lab', 'seminar', 'tutorial'
    capacity INTEGER,
    enrolled INTEGER DEFAULT 0,
    waitlist INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'open', -- 'open', 'closed', 'cancelled'
    instructor_info JSONB, -- Instructor details
    schedule JSONB, -- Days, times, locations
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exam schedules
CREATE TABLE exam_schedules (
    id SERIAL PRIMARY KEY,
    course_section_id INTEGER REFERENCES course_sections(id) ON DELETE CASCADE,
    exam_type VARCHAR(50), -- 'final', 'midterm', 'quiz'
    exam_date DATE,
    start_time TIME,
    end_time TIME,
    location VARCHAR(255),
    duration_minutes INTEGER,
    special_instructions TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Instructors/Faculty members (for future expansion)
CREATE TABLE instructors (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    employee_id VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    title VARCHAR(100), -- Professor, Associate Professor, etc.
    department VARCHAR(255),
    email VARCHAR(255),
    office_location VARCHAR(255),
    research_areas TEXT[],
    ratings JSONB, -- Average ratings, review counts, etc.
    salary_info JSONB, -- If available publicly
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data synchronization tracking
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    data_type VARCHAR(100), -- 'faculties', 'courses', 'schedules', etc.
    sync_status VARCHAR(50), -- 'success', 'failed', 'partial'
    records_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB
);

-- Indexes for performance
CREATE INDEX idx_universities_code ON universities(code);
CREATE INDEX idx_faculties_university_code ON faculties(university_id, code);
CREATE INDEX idx_subjects_university_code ON subjects(university_id, code);
CREATE INDEX idx_courses_university_code ON courses(university_id, code);
CREATE INDEX idx_courses_subject ON courses(subject_id);
CREATE INDEX idx_course_sections_course_term ON course_sections(course_id, term_id);
CREATE INDEX idx_exam_schedules_section ON exam_schedules(course_section_id);
CREATE INDEX idx_instructors_university ON instructors(university_id);
CREATE INDEX idx_sync_logs_university_type ON sync_logs(university_id, data_type);

-- JSONB indexes for common queries
CREATE INDEX idx_courses_metadata_gin ON courses USING GIN (metadata);
CREATE INDEX idx_faculties_metadata_gin ON faculties USING GIN (metadata);
CREATE INDEX idx_subjects_metadata_gin ON subjects USING GIN (metadata);
CREATE INDEX idx_course_sections_schedule_gin ON course_sections USING GIN (schedule);
CREATE INDEX idx_instructors_ratings_gin ON instructors USING GIN (ratings);
