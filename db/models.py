import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, text
from sqlalchemy.dialects.postgresql import JSONB, UUID, TIMESTAMP
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    url = Column(String, nullable=False, unique=True)
    country = Column(String(255), nullable=False)
    language = Column(String(2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    # Relationships
    jobs = relationship("Job", back_populates="source")

class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    # Relationships
    jobs = relationship("Job", back_populates="company")

class Job(Base):
    __tablename__ = 'jobs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    source_id = Column(Integer, ForeignKey('sources.id', ondelete='SET NULL'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('companies.id', ondelete='SET NULL'), nullable=False, index=True)
    
    title = Column(String(255), nullable=True)
    description = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False, index=True)
    
    salary_min = Column(Numeric, nullable=True)
    salary_max = Column(Numeric, nullable=True)
    currency = Column(String(3), nullable=True)
    
    location = Column(String(255), nullable=True)
    job_type = Column(String(255), nullable=True)
    
    posted_date = Column(DateTime(timezone=True), nullable=True, index=True)
    scraped_at = Column(TIMESTAMP(timezone=True), nullable=False)
    
    raw_data = Column(JSONB, nullable=False) 
    
    created_at = Column(DateTime(timezone=True), server_default=text('now()'), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'))

    # Relationships
    source = relationship("Source", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")