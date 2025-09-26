# Manager class for document ingestion and processing
import os
from pydantic_ai import Agent, BinaryContent
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from extract_msg import Message
from prompt import system_prompt
load_dotenv()



class Output(BaseModel):
	insurance_company: str = Field(..., description="Name of the insurance company")
	quarter: str = Field(..., description="Quarter for the report, e.g., 'Q2 2024'")
	total_income: float = Field(..., description="Total income for the period")
	commision: float = Field(..., description="Commission amount")
	premium_tax: float = Field(..., description="Premium tax amount")
	borderaux: list[dict] = Field(default_factory=list, description="List of borderaux table entries")
	issues: list[str] = Field(default_factory=list, description="List of issues found during processing")
    
def calculate_claims_paid(
	borderaux: list[dict],
	commision: float,
	total_income: float,
	premium_tax: float
) -> float:
	"""
	Tool to calculate total claims paid using the formula:
	Claims Paid = (Commission% × Total Income) + (Premium Tax × Total Income)
	Args:
		borderaux (list[dict]): List of borderaux entries (not used in this formula).
		commision (float): Commission percentage (e.g., 0.05 for 5%).
		total_income (float): Total income for the period.
		premium_tax (float): Premium tax percentage (e.g., 0.02 for 2%).
	Returns:
		float: Total claims paid.
	"""
	return (commision * total_income) + (premium_tax * total_income)

class Manager:
	"""
	Handles document ingestion and processing for claims documents.
	"""
	def __init__(self):
		self.agent = Agent(
			"google-gla:gemini-2.0-flash",
			output_type=Output,
			system_prompt=system_prompt,
			tools={
				"calculate_claims_paid": calculate_claims_paid
			}
		)
		self.marine_attachments = []

	def ingest_file(self, file_path):
		"""
		Ingests a .msg file, extracts attachments, and returns info about marine PDFs.
		Args:
			file_path (str): Path to the uploaded .msg file.
		Returns:
			dict: {'attachment_count': int, 'attachment_names': list[str]}
		"""
		message = Message(file_path)
		self.marine_attachments = [
			attachment for attachment in getattr(message, 'attachments', [])
			if hasattr(attachment, 'name') and hasattr(attachment, 'data')
			and "marine" in attachment.name.casefold() and attachment.name.lower().endswith('.pdf')
		]
		attachment_names = [attachment.name for attachment in self.marine_attachments]
		return {
			'attachment_count': len(self.marine_attachments),
			'attachment_names': attachment_names
		}

	def process_using_model(self):
		data = []
		for attachment in self.marine_attachments:
			try:
				result = self.agent.run_sync(
					[
						BinaryContent(
							attachment.data,
							media_type="application/pdf"
						)
					]
				).output
				data.append(result)
			except Exception as e:
				data.append(Output(
					insurance_company="",
					quarter="",
					total_income=0.0,
					commision=0.0,
					premium_tax=0.0,
					borderaux=[],
					issues=[f"Error processing attachment {getattr(attachment, 'name', '')}: {e}"]
				))
		return data
            
            
            
