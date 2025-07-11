"""
Code samples for vector database quickstart pages:
    https://redis.io/docs/latest/develop/get-started/vector-database/
"""
import orjson
import json
import time
from typing import List
import numpy as np
import pandas as pd
import requests
import re
import pyodbc
from getpass import getpass

from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import redis
from redis.commands.search.field import TagField, VectorField, NumericField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
VECTOR_DIMENSIONS = 1024
INDEX_NAME = "story_index"
DOC_PREFIX = "business_question:"

server = 'tcp:sql404server.database.windows.net,1433'
database = 'SupermarketDB'
username = 'odl_user_1782423@cloudlabssandbox.onmicrosoft.com'
password = 'hawu90KBV*NX'

# Connection string
connection_string = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server={server};"
    f"Database={database};"
    f"Uid={username};"
    f"Pwd={password};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
    f"Authentication=ActiveDirectoryPassword;"
)

json_data = [
    {
        "id": 1,
        "business_question": "Which are the gluten free products present in the store and the price?",
        "business_query": "SELECT ItemName, Category, Brand, Price FROM [dbo].[SupermarketItems] WHERE allergy like '%gluten free%'"
    },
    {
        "id": 2,
        "business_question": "I want to buy the 'Choco Milk Pack' from the 'FreshFarm', where I can find it? ",
        "business_query": "SELECT Location FROM [dbo].[SupermarketItems] WHERE ItemName = 'Choco Milk Pack' AND Brand = 'FreshFarm'"
    },
    {
        "id": 3,
        "business_question": "Can you please show the Nutri Score of this item?",
        "business_query": "SELECT Location FROM [dbo].[SupermarketItems] WHERE ItemName = 'Choco Milk Pack' AND Brand = 'FreshFarm'"
    },
    {
        "id": 4,
        "business_question": "Can you please show me the receipe for a Pizza?",
        "business_query": "SELECT IngredientName, Quantity, RecipeName FROM [dbo].[Ingredients] as ing INNER JOIN [dbo].[Recipes] as rec ON ing.RecipeID = rec.RecipeID INNER JOIN [dbo].[SupermarketItems] as smi ON smi.ItemName = ing.IngredientName where rec.RecipeName like '%Pizza%'" 
    },
    {
        "id": 5,
        "business_question": "Can you please show me the item I should by to cook the pizza and the information about the are where I should find them?",
        "business_query": "SELECT ItemName, smi.Category, Brand, Price, Location FROM [dbo].[Ingredients] as ing INNER JOIN [dbo].[Recipes] as rec ON ing.RecipeID = rec.RecipeID INNER JOIN [dbo].[SupermarketItems] as smi ON smi.ItemName = ing.IngredientName where rec.RecipeName like '%Pizza%'"
    },
    {
        "id": 6,
        "business_question": "What is the cost of this recipe?",
        "business_query": "SELECT SUM(Price) FROM [dbo].[Ingredients] as ing INNER JOIN [dbo].[Recipes] as rec ON ing.RecipeID = rec.RecipeID INNER JOIN [dbo].[SupermarketItems] as smi ON smi.ItemName = ing.IngredientName where rec.RecipeName like '%Pizza%'"
    },
    {
        "id": 7,
        "business_question": "Can you please show me the receipe for a Bolognese?",
        "business_query": "SELECT IngredientName, Quantity, RecipeName FROM [dbo].[Ingredients] as ing INNER JOIN [dbo].[Recipes] as rec ON ing.RecipeID = rec.RecipeID INNER JOIN [dbo].[SupermarketItems] as smi ON smi.ItemName = ing.IngredientName where rec.RecipeName like '%Bolognese%'"
    },
    {
        "id": 8,
        "business_question": "Can you show me the instruction to cook Bolognese?",
        "business_query": "SELECT StepNumber, StepDescription  FROM [dbo].[Instructions] inst INNER JOIN [dbo].[Recipes] as rec ON inst.RecipeID = rec.RecipeID where rec.RecipeName like '%Bolognese%' ORDER BY StepNumber ASC"
    },
    {
        "id": 9,
        "business_question": "Please show me the products with NutriScore 'A'",
        "business_query": "SELECT ItemName, Brand, NutriScore FROM [dbo].[SupermarketItems] WHERE NutriScore = 'A'"
    },
    {
        "id": 10,
        "business_question": "Show me the the less expensive item with Nutriscore A",
        "business_query": "SELECT ItemName, Brand, NutriScore, Price FROM [dbo].[SupermarketItems] WHERE NutriScore = 'A' ORDER BY Price ASC"
    },
    {
        "id": 11,
        "business_question": "Can you give me the list of most selled product with Nutriscore 'A'?",
        "business_query": "SELECT TOP 5  ItemName, Brand, NutriScore, Price FROM [dbo].[SupermarketItems] WHERE NutriScore = 'A' ORDER BY SalesPerMonth DESC"
    }

]


# Instantiate the Ollama embedding model
embeddings_model = OllamaEmbeddings(model="mxbai-embed-large")


def extract_first_sql_query(text):
    # Pattern to match SQL code blocks
    pattern = r'```sql\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    
    if matches:
        # Return the first match, stripping any whitespace
        return matches[0].strip()
    else:
        return None

class Story:
    def __init__(self, id: int = None, business_question: str = None, business_query: str = None, embedding: List[float] = None, embeddingsize: int = None):
        self.id = id
        self.business_question = business_question
        self.business_query = business_query
        self.embedding = embedding
        self.embeddingsize = embeddingsize

    def print(self):
        print(f"ID:          {self.id}")
        print(f"User Question:       {self.business_question}")
        print(f"Business Query:       {self.business_query}")
        print(f"Embedding:   {self.embedding}")
        print(f"Embeddingsize:   {self.embeddingsize}")

    def to_json(self) -> str:
        story_dict = {
            'id': self.id,
            'business_question': self.business_question,
            'business_query': self.business_query,
            'embedding': self.embedding,
            'embeddingsize': self.embeddingsize
        }
        return orjson.dumps(story_dict).decode('utf-8')
        #return json.dumps(self)


client = redis.Redis(host="redis-18805.c282.east-us-mz.azure.redns.redis-cloud.com", port=18805,password="xB9B1BtFHxu1CvzNoRlE5yiIy3N0fpD1", decode_responses=True)
print("Main")
# Clear all data in all databases
client.flushall()
print("All data in all Redis databases have been cleared.")
print("Deleting index")
#client.ft(INDEX_NAME).dropindex(delete_documents=True)
res = client.ping()
print("ping  " + str(res))

def create_index(vector_dimensions: int):
    try:
        # check to see if index exists
        client.ft(INDEX_NAME).info()
        print("Index already exists!")
    except:
        # schema
        schema = (
            NumericField('id'),
            TextField('business_question'),
            TextField('business_query'),
            VectorField('embedding',
                'FLAT', {
                "TYPE": "FLOAT32",
                "DIM": vector_dimensions,  # Adjust the dimension according to your embedding size
                "DISTANCE_METRIC": "COSINE"
            })
    )

        # index Definition
        definition = IndexDefinition(prefix=[DOC_PREFIX], index_type=IndexType.HASH)

        # create Index
        client.ft(INDEX_NAME).create_index(fields=schema, definition=definition)


print("creating index")
create_index(vector_dimensions=VECTOR_DIMENSIONS)

print(" Write to Redis")
# write data
pipe = client.pipeline()
for obj in json_data:
    # define key
    #key = f"story:{obj['id']}"
    key = f"business_question:{obj['id']}"
    # create a random "dummy" vector
    embeddings = embeddings_model.embed_documents(obj['business_question'])[0]
    obj["embedding"] = np.array(embeddings, dtype=np.float32).tobytes()
    # HSET
    pipe.hset(key, mapping=obj)
res = pipe.execute()


question = "Can you please provide the detailed receipe for the Pizza followed by the ingredints with relative quantity?"
#question = "Can you give me the list of most selled product with Nutriscore \"A\"?"
print("UserQuestion is ...: " + question)
userQuestion= embeddings_model.embed_documents(question)[0]

# Define the query and query parameters
#query = Query("(*)=>[KNN 6 @embedding $vec AS score]").sort_by("score").dialect(2).paging(0, 100)
#query_params = {"vec": np.array(userQuestion, dtype=np.float32).tobytes()}

query = Query("(*)=>[KNN 6 @embedding $vec AS score]").return_fields("id", "business_question", "business_query", "score").sort_by("score").dialect(2).paging(0, 100)
query_params = {"vec": np.array(userQuestion, dtype=np.float32).tobytes()}

print("Perform the search###############")
results = client.ft(INDEX_NAME).search(query, query_params).docs

print("Print the results################")
for doc in results:
    print(doc.id)
    print(doc.business_question)
    print(doc.business_query)

#userQuestion = results[0].business_question



business_question = str(results)
template = """
You are a Postgres expert. 
Generate a SQL query to answer the {question}. 
Your response must be based only on the provided context and must strictly follow the response guidelines and format instructions.
=== Response Guidelines
Return ONLY the SQL query. Do not include any instructions, explanations, comments, or additional details or lines in the output.
If the provided context is sufficient, generate a valid SQL query without any explanations, comments, or additional text.

When the query: {query} is not None, it means that the query execution throw this kind of {exception}  in the previous query generation.. use this information to generate again the correct query
.
If the context is insufficient to generate a query, explain briefly why and conclude with: Decision: insufficient.

When questions are phrased differently but have the same intent, rephrase the question to match the available data context and generate the query. 
If context is still lacking, indicate insufficient context clearly.

Use the most relevant table(s) available.

Leverage previous conversations and context to craft an accurate response.

Ensure the SQL is postgres-compliant, executable, and free of syntax errors.

Do not generate any DDL or DML queries.

If a similar question was asked before and a query was provided, use that query if applicable.

Do not prepend or append any string or phrase to the SQL. The output must be the raw SQL only.

You use COUNT(DISTINCT column) instead of COUNT(column) unless it is certain that duplicates are not possible or desired.


===Additional Context

The following details are for the "SupermarketItems" table in the  schema:

Table Name	Column Name	Data Type	Description
SupermarketItems	ID	nvarchar(10)	Unique item ID (not primary key).
SupermarketItems	ItemName	nvarchar(255)	Name of the supermarket item.
SupermarketItems	Category	nvarchar(100)	Category (e.g., Dairy, Produce).
SupermarketItems	Brand	nvarchar(100)	Brand name of the item.
SupermarketItems	Price	float	Price of the item.
SupermarketItems	StockQuantity	int	Number of units available.
SupermarketItems	ExpiryDate	date	Expiration date.
SupermarketItems	Supplier	nvarchar(100)	Supplier name.
SupermarketItems	Allergy	nvarchar(50)	Allergy info (e.g., Nuts, Gluten).
SupermarketItems	Location	nvarchar(50)	Store section where the item is found.
SupermarketItems	NutriScore	nvarchar(5)	Nutritional score (e.g., A to E).
SupermarketItems	SalesPerMonth	int	Number of units sold per month.

The following details are for the "Recipes" table in the  schema:
Table Name	Column Name	Data Type	Description
Recipes	RecipeID	int	Unique ID for the recipe. Primary Key.
Recipes	RecipeName	nvarchar(100)	Name of the recipe.
Recipes	Description	nvarchar(255)	Short recipe description.
Recipes	Category	nvarchar(50)	Recipe category (e.g., Dessert, Vegan).

The following details are for the "Instructions" table in the  schema:
Table Name	Column Name	Data Type	Description
Instructions	InstructionID	int	Unique ID for each instruction. Primary Key.
Instructions	RecipeID	int	Linked recipe ID. Foreign Key → Recipes(RecipeID).
Instructions	StepNumber	int	Order of the instruction step.
Instructions	StepDescription	nvarchar(500)	Description of what to do in that step.

The following details are for the "Ingredients" table in the  schema:
Table Name	Column Name	Data Type	Description
Ingredients	IngredientID	int	Unique ID for each ingredient. Primary Key.
Ingredients	RecipeID	int	Linked recipe ID. Foreign Key → Recipes(RecipeID).
Ingredients	IngredientName	nvarchar(100)	Name of the ingredient.
Ingredients	Quantity	nvarchar(100)	Quantity (e.g., "2 cups", "100g").


here the schema of "SupermarketItems":
/****** Object:  Table [dbo].[SupermarketItems]    Script Date: 09/07/2025 12:12:54 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[SupermarketItems](
	[ID] [nvarchar](10) NULL,
	[ItemName] [nvarchar](255) NULL,
	[Category] [nvarchar](100) NULL,
	[Brand] [nvarchar](100) NULL,
	[Price] [float] NULL,
	[StockQuantity] [int] NULL,
	[ExpiryDate] [date] NULL,
	[Supplier] [nvarchar](100) NULL,
	[Allergy] [nvarchar](50) NULL,
	[Location] [nvarchar](50) NULL,
	[NutriScore] [nvarchar](5) NULL,
	[SalesPerMonth] [int] NULL
) ON [PRIMARY]
GO

here the schema of "Recipes":
/****** Object:  Table [dbo].[Recipes]    Script Date: 09/07/2025 12:12:45 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Recipes](
	[RecipeID] [int] IDENTITY(1,1) NOT NULL,
	[RecipeName] [nvarchar](100) NULL,
	[Description] [nvarchar](255) NULL,
	[Category] [nvarchar](50) NULL,
PRIMARY KEY CLUSTERED 
(
	[RecipeID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

here the schema of "Instructions":
/****** Object:  Table [dbo].[Instructions]    Script Date: 09/07/2025 12:12:37 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Instructions](
	[InstructionID] [int] IDENTITY(1,1) NOT NULL,
	[RecipeID] [int] NULL,
	[StepNumber] [int] NULL,
	[StepDescription] [nvarchar](500) NULL,
PRIMARY KEY CLUSTERED 
(
	[InstructionID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[Instructions]  WITH CHECK ADD FOREIGN KEY([RecipeID])
REFERENCES [dbo].[Recipes] ([RecipeID])
GO

here the schema of "Ingredients":
/****** Object:  Table [dbo].[Ingredients]    Script Date: 09/07/2025 12:12:26 ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[Ingredients](
	[IngredientID] [int] IDENTITY(1,1) NOT NULL,
	[RecipeID] [int] NULL,
	[IngredientName] [nvarchar](100) NULL,
	[Quantity] [nvarchar](100) NULL,
PRIMARY KEY CLUSTERED 
(
	[IngredientID] ASC
)WITH (STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO

ALTER TABLE [dbo].[Ingredients]  WITH CHECK ADD FOREIGN KEY([RecipeID])
REFERENCES [dbo].[Recipes] ([RecipeID])
GO


===here the list of user question and relative query that you can use as examples to generate the right query:
{business_question}

"""

prompt = PromptTemplate(template=template, input_variables=["question", "business_question"])
# Initialize the OpenAI language model with specified settings
#llm = OllamaLLM(model="llama3:8b")
llm = OllamaLLM(model="deepseek-v2")

# Create an LLMChain with the prompt and language model
chain = prompt | llm



exception = None
query = None
rows = None

while exit:
    print("############# Starting While #############")
    output = chain.invoke({"question": question , "business_question": business_question, "exception": exception, "query": query})
    
    try:
        conn = pyodbc.connect(connection_string)
        if conn:
            cursor = conn.cursor()
            #output = extract_first_sql_query(output)
            print(output)
            query = output
            cursor.execute(output)
            rows = cursor.fetchall()
        # Display results
            for row in rows:
                print(row)   
            conn.close()
        else:
            conn = pyodbc.connect(connection_string)
            cursor = conn.cursor()
            #output = extract_first_sql_query(output)
            print(output)
            query = output
            cursor.execute(output)
            rows = cursor.fetchall()
        # Display results
            for row in rows:
                print(row)   
            conn.close()
            #print("output: ####" + " " + output)
            #output = extract_first_sql_query(output)
            # Print the output
            #print("question: " + " " + question)
            #print("answer: " + " " + output)
        exit = False     
    except Exception as e:
        exception = str(e) 
        exit = True
        # Print error message if something goes wrong
        print(f"An error occurred: {e}")
    
    except pyodbc.Error as e:
        print(f"Error connecting to database: {e}")

print("############# End of  While #############")
print("Final SQL Query", output)
    # finally:
    #     # Close connection
    #     if 'conn' in locals():
    #         conn.close()
    #         print("\nConnection closed.")

### Another Model
data = str(rows)

template = """
You are an concierge of a Grocery Shop and you provide an answer to all irrespective of their age.
=== Response Guidelines
Always answer in a kind and friendly language. 
Make the answer in such a way that it feels like a conversational language for all types of peoples, especially elder peoples.
Answer in the precise and in a simple sentences and in a natural language
Do NOT print in the output <think> </think> content , strictly just provide an answer 
Answer the question clearly and directly. Do not include any internal thoughts or <think> tags.
Also answer in such a way that, the text i.e answer can be translted to Speech.
Question: {question} 
read this information: {data} answer to this question.
Please provide an answer thet is shorter as possible.
Please use only the data which is been provided to answer the question. 

Answer:  
"""

prompt = PromptTemplate(template=template, input_variables=["question", "data"])

# Initialize the OpenAI language model with specified settings
#deepseek = OllamaLLM(model="deepseek-r1:1.5b")
deepseek = OllamaLLM(model="deepseek-v2") 
# Create an LLMChain with the prompt and language model
chain = prompt | deepseek

output = chain.invoke({"question": question , "data": data})

print("deepseek-v2-->", output) 
