import os
import base64
import warnings
from typing import Optional, TypedDict, Dict, Any
from dotenv import load_dotenv

# LangChain & LangGraph Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

# 1. Setup & Configuration
# ---------------------------------------------------------
load_dotenv()

# Suppress LangSmith UUID warning
warnings.filterwarnings("ignore", message="LangSmith now uses UUID v7")

# Configure LangSmith (Ensure you have your API key in .env)
# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_PROJECT"] = "Bill_Extraction_Project"
# os.environ["LANGCHAIN_API_KEY"] = "your-langchain-api-key"
# os.environ["GOOGLE_API_KEY"] = "your-google-api-key"

# NOTE: "Gemini Pro 3" is not yet a standard public endpoint name. 
# We use 'gemini-1.5-pro-latest' which is the current state-of-the-art Pro model.
# You can switch this to 'gemini-2.0-flash-exp' or other models as they release.
MODEL_NAME = "gemini-2.5-flash"

# 2. Define the Data Schema (Matches your Prompt Requirements)
# ---------------------------------------------------------
class Provider(BaseModel):
    name: Optional[str] = Field(description="Name of the service provider")
    contact_info: Optional[str] = Field(description="Phone number or email if prominent")

class DocumentInfo(BaseModel):
    type: Optional[str] = Field(description="Type of document, e.g., Electronic Bill, Invoice")
    number: Optional[str] = Field(description="Invoice or Document ID number")
    issue_date: Optional[str] = Field(description="Date of issue in YYYY-MM-DD format")

class Customer(BaseModel):
    name: Optional[str] = Field(description="Name of the customer")
    client_id: Optional[str] = Field(description="Account or Customer Number")
    tax_id: Optional[str] = Field(description="RUT/SSN/Tax ID if available")
    address: Optional[str] = Field(description="Billing address")

class Financials(BaseModel):
    total_amount: Optional[float] = Field(description="Total amount to pay as a number")
    currency: Optional[str] = Field(description="ISO currency code (e.g., CLP, USD)")
    due_date: Optional[str] = Field(description="Payment due date in YYYY-MM-DD format")
    status: Optional[str] = Field(description="Payment status inferred from context (Pending, Paid, Overdue)")

class PeriodAndUsage(BaseModel):
    billing_period_start: Optional[str] = Field(description="Start date of billing period YYYY-MM-DD")
    billing_period_end: Optional[str] = Field(description="End date of billing period YYYY-MM-DD")
    cutoff_date: Optional[str] = Field(description="Date when service might be cut YYYY-MM-DD")
    tariff_type: Optional[str] = Field(description="Rate category or tariff type")

class BillExtraction(BaseModel):
    """Main schema for the bill extraction task."""
    provider: Provider
    document: DocumentInfo
    customer: Customer
    financials: Financials
    period_and_usage: PeriodAndUsage

# 3. Define the Graph State
# ---------------------------------------------------------
class AgentState(TypedDict):
    image_path: str
    extracted_data: Optional[Dict[str, Any]]
    error: Optional[str]

# 4. Define Graph Nodes
# ---------------------------------------------------------
def load_and_encode_image(state: AgentState):
    """Reads the image file and encodes it to base64."""
    try:
        image_path = state["image_path"]
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
        return {"image_data": image_data}
    except Exception as e:
        return {"error": f"Failed to load image: {str(e)}"}

def extract_data_node(state: AgentState):
    """Calls Gemini with the image and structured output request."""
    if state.get("error"):
        return state

    # Initialize the LLM with structured output
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        temperature=0
    ).with_structured_output(BillExtraction)

    # Define the specific system prompt based on your "Optimal Prompt" design
    system_instruction = """
    You are an automated document processing agent specialized in data extraction.
    Analyze the provided image of a service bill. Extract the key metadata into the requested JSON structure.
    
    1. Identify provider, customer, dates, and financials.
    2. Normalize dates to YYYY-MM-DD.
    3. Normalize amounts to numbers (remove $ and dots).
    4. If a field is missing, return null.
    """

    # Prepare the message payload for Vision
    # We need to pass the image data retrieved from the previous step (not stored in state to save memory, 
    # but for this example, we'll re-read or assume it's passed via a wrapper if using a persistent store. 
    # Here we'll just re-encode for simplicity of the node isolation).
    
    try:
        # Re-encoding locally for the node or passing via state key if we added it to TypedDict.
        # Let's read it again to keep state clean or assume it was passed.
        with open(state["image_path"], "rb") as image_file:
            image_b64 = base64.b64encode(image_file.read()).decode("utf-8")

        message = HumanMessage(
            content=[
                {"type": "text", "text": system_instruction},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                },
            ]
        )

        # Invoke Gemini
        response: BillExtraction = llm.invoke([message])
        
        # Convert Pydantic model to Dict for the state
        return {"extracted_data": response.model_dump()}

    except Exception as e:
        return {"error": f"Extraction failed: {str(e)}"}

# 5. Build the LangGraph
# ---------------------------------------------------------
def build_extraction_graph():
    workflow = StateGraph(AgentState)

    # Add Nodes
    workflow.add_node("extract", extract_data_node)

    # Set Entry Point
    workflow.set_entry_point("extract")

    # Set Finish
    workflow.add_edge("extract", END)

    return workflow.compile()

# 6. Main Execution
# ---------------------------------------------------------
if __name__ == "__main__":
    # Example Usage
    # Replace this with the path to your actual image file
    #IMAGE_FILE = "./test_data/chilquinta_electricidad.jpg" 
    IMAGE_FILE = "./test_data/cge_electricidad.png" 
    #IMAGE_FILE = "./test_data/aguas_andinas.jpg" 
    #IMAGE_FILE = "./test_data/luzparral_electricidad.jpg" 


    if not os.path.exists(IMAGE_FILE):
        print(f"Error: File {IMAGE_FILE} not found. Please place the image in the directory.")
    else:
        print(f"--- Starting Extraction for {IMAGE_FILE} ---")
        
        app = build_extraction_graph()
        
        # Run the graph
        result = app.invoke({"image_path": IMAGE_FILE})

        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            import json
            print("\n--- Extracted JSON Data ---")
            print(json.dumps(result["extracted_data"], indent=2, ensure_ascii=False))