from sqlmodel import SQLModel, Field
    
class BuoyantWeight(SQLModel, table=True):
    __tablename__ = 'BuoyantWeightData'
    id: int = Field(default=None, primary_key=True)
    sample: str
    mass: float
    unit: str
    status: str
    salinity: float = 35.0
    temperature: float = 25.0
    notes: str = ''
    timestamp: str
