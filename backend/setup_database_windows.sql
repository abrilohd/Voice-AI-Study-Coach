-- Database setup script for Voice AI Study Coach (Windows)
-- Run this with: psql -U postgres -f setup_database_windows.sql

-- Drop database if it exists (be careful in production!)
DROP DATABASE IF EXISTS voice_ai_study_coach;

-- Create database
CREATE DATABASE voice_ai_study_coach;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE voice_ai_study_coach TO postgres;
