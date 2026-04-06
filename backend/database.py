from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import

DATABASE_URL=os.env.DATABASE_URL

engine = create_engine(DATABASE_URL)
Session_Locsl = sessionmaker(bind=engine)

Base = declarative_base()