# src/llm_handler.py
import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from src.database import get_product_data, update_product_stock

load_dotenv()

# Initialize Azure OpenAI LLM
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0.7 # Adjust for creativity/determinism
)

def retrieve_and_augment(user_query: str):
    """
    Retrieves relevant product information based on user query and
    augments the LLM prompt with this context.
    """
    # Basic keyword extraction for database query
    keywords = user_query.lower().split()
    
    # Heuristic to determine if a specific product or category is being asked
    # This can be improved with more sophisticated NLP or a dedicated intent classification
    
    product_name_query = None
    category_query = None
    brand_query = None

    if "stock" in user_query.lower() or "quantity" in user_query.lower():
        # Look for product names in the query
        for product in ["milk", "eggs", "bread", "beef", "salmon", "broccoli", "apples", "cheese", "chicken", "pasta", "tomato sauce", "olive oil", "coffee", "tea", "dish soap", "paper towels", "detergent", "shampoo", "toothpaste", "vitamins"]:
            if product in user_query.lower():
                product_name_query = product
                break
    
    # Try to identify category
    if "dairy" in user_query.lower():
        category_query = "Dairy"
    elif "meat" in user_query.lower():
        category_query = "Meat"
    elif "vegetables" in user_query.lower():
        category_query = "Vegetables"
    elif "fruits" in user_query.lower():
        category_query = "Fruits"
    elif "pantry" in user_query.lower():
        category_query = "Pantry"

    relevant_data = []
    if product_name_query:
        relevant_data = get_product_data(query=product_name_query)
    elif category_query:
        relevant_data = get_product_data(category=category_query)
    else:
        # Fallback to general search if no specific intent is clear
        relevant_data = get_product_data(query=user_query) # Use the full query as a general search

    if not relevant_data:
        return "No specific product information found in the database based on your query."
    
    formatted_data = "\n".join([str(item) for item in relevant_data])
    return f"The following relevant product information is available:\n{formatted_data}\n"

def handle_stock_update_request(user_query: str) -> str:
    """
    Attempts to parse a stock update request from the user query
    and update the database.
    This is a simplified example and needs robust NLP for real-world use.
    """
    # Example: "Update stock for Whole Milk to 250" or "Change quantity of item ID 1 to 250"
    
    product_id = None
    new_quantity = None
    item_name = None

    # Very basic parsing
    if "update stock for" in user_query.lower():
        parts = user_query.lower().split("update stock for", 1)[1].strip().split("to")
        if len(parts) == 2:
            item_name_part = parts[0].strip()
            try:
                new_quantity = int(parts[1].strip())
            except ValueError:
                return "I couldn't understand the new quantity. Please provide a number."
            
            # Attempt to find the product ID by name
            # This is a simplification; ideally, you'd confirm with the user if multiple matches exist
            products = get_product_data(query=item_name_part)
            if products:
                # Taking the first match for simplicity
                product_id = products[0]['ID']
                item_name = products[0]['Item Name']
            else:
                return f"I couldn't find a product matching '{item_name_part}'."

    elif "change quantity of item id" in user_query.lower():
        parts = user_query.lower().split("change quantity of item id", 1)[1].strip().split("to")
        if len(parts) == 2:
            try:
                product_id = int(parts[0].strip())
                new_quantity = int(parts[1].strip())
            except ValueError:
                return "I couldn't understand the product ID or new quantity. Please provide numbers."
            
            # Verify product exists
            product_info = get_product_data(query=f"id={product_id}") # Small hack: query by ID
            if product_info:
                item_name = product_info[0]['Item Name']
            else:
                return f"No product found with ID {product_id}."


    if product_id is not None and new_quantity is not None:
        success = update_product_stock(product_id, new_quantity)
        if success:
            return f"Successfully updated stock for '{item_name}' (ID: {product_id}) to {new_quantity}."
        else:
            return f"Failed to update stock for '{item_name}' (ID: {product_id}). There was a database error."
    else:
        return "I can update product stock. Please tell me the item name or ID and the new quantity. (e.g., 'Update stock for Whole Milk to 250' or 'Change quantity of item ID 1 to 250')"


def get_llm_response(user_input: str) -> str:
    """
    Handles the overall workflow:
    1. Determines if the user intent is to update data or just query.
    2. Retrieves relevant information from the database.
    3. Augments the LLM prompt.
    4. Gets a response from the LLM.
    """
    
    # Basic intent detection: check for keywords indicating an update request
    if "update stock" in user_input.lower() or "change quantity" in user_input.lower():
        return handle_stock_update_request(user_input)

    # If not an update request, proceed with information retrieval and query
    context = retrieve_and_augment(user_input)
    
    # Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an intelligent assistant for a retail store. Your primary role is to provide information about product inventory and assist staff/customers. Use the provided product information to answer questions. If the information isn't available, state that you don't know but offer general assistance. Do not make up product details. Be concise and helpful. Today's date is July 3, 2025."),
        ("human", "Here is some relevant product information from our database:\n{context}\n\nUser query: {query}")
    ])

    # Create the Langchain chain
    chain = (
        {"context": lambda x: context, "query": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain.invoke(user_input)

if __name__ == "__main__":
    print("--- LLM Interaction Demo ---")

    # Example 1: Query about product stock
    query1 = "What is the stock quantity for Whole Milk?"
    print(f"\nUser: {query1}")
    response1 = get_llm_response(query1)
    print(f"Assistant: {response1}")

    # Example 2: Query about a category
    query2 = "Tell me about products in the Dairy category."
    print(f"\nUser: {query2}")
    response2 = get_llm_response(query2)
    print(f"Assistant: {response2}")

    # Example 3: Query about a non-existent product
    query3 = "Do you have any 'Unobtainium' in stock?"
    print(f"\nUser: {query3}")
    response3 = get_llm_response(query3)
    print(f"Assistant: {response3}")

    # Example 4: Attempt a stock update
    # First, get current stock
    current_milk_stock = get_product_data(query="Whole Milk")[0]['Stock Quantity']
    print(f"\n--- Stock Update Demo ---")
    print(f"Current Whole Milk stock before update: {current_milk_stock}")
    
    update_query = "Update stock for Whole Milk to 280"
    print(f"\nUser: {update_query}")
    update_response = get_llm_response(update_query)
    print(f"Assistant: {update_response}")

    # Verify update
    updated_milk_stock = get_product_data(query="Whole Milk")[0]['Stock Quantity']
    print(f"Current Whole Milk stock after update: {updated_milk_stock}")

    # Example 5: Another stock update by ID
    update_query_id = "Change quantity of item ID 2 to 140"
    print(f"\nUser: {update_query_id}")
    update_response_id = get_llm_response(update_query_id)
    print(f"Assistant: {update_response_id}")

    # Example 6: Revert stock for demo
    get_llm_response(f"Update stock for Whole Milk to {current_milk_stock}")
    get_llm_response(f"Change quantity of item ID 2 to 150")
    print("\n--- Stock reverted for demo purposes ---")