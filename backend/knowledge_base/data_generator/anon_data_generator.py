import dspy
import json
import re
from typing import Dict, List
import os

# Configure dspy with Ollama
lm = dspy.LM("ollama_chat/llama3.1:latest", api_base="http://localhost:11434", api_key="")
dspy.configure(lm=lm)

class EntityExtractor(dspy.Signature):
    """Extract entities from text"""
    text = dspy.InputField(desc="Case study text")
    entities = dspy.OutputField(desc="JSON with lists of companies, people, products and features")

class AnonEntityGenerator(dspy.Signature):
    """ Replace the company/entity/person names to fictional ones. Rephrase the feature/products/services ."""
    text = dspy.InputField(desc="Name of entity")
    name = dspy.OutputField(desc="Fictional name of entity")

class Rephraser(dspy.Signature):
    """ Rephrase the feature/products/services ."""
    text = dspy.InputField(desc="Name of service")
    name = dspy.OutputField(desc="Rephrased text of the service while retaining the meaning.")

class Anonymizer:
    def __init__(self):
        self.replacement_dict = {}
        self.entity_counters = {
            'company': 1,
            'person': 1,
            'product': 1,
            'feature': 1
        }
    
    def extract_entities(self, text: str) -> Dict:
        """Extract entities using DSPy and Ollama"""
        extractor = dspy.ChainOfThought(EntityExtractor)
        result = extractor(text=text)
        
        try:
            # Try to parse the JSON output
            entities = json.loads(result.entities)
            return entities
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            print("Failed to parse JSON, using fallback extraction")
            return self.fallback_entity_extraction(text)

    def generate_fictional_name(self, text: str) -> Dict:
        """Generate the fictional name"""
        extractor = dspy.ChainOfThought(AnonEntityGenerator)
        result = extractor(text=text)
        
        try:
            return result.name
        except:
            print("Failed to generate fictional name")
    
    def generate_rephraser(self, text: str) -> Dict:
        """Generate the rephrased text"""
        extractor = dspy.ChainOfThought(Rephraser)
        result = extractor(text=text)
        
        try:
            return result.name
        except:
            print("Failed to generate fictional name")

    def fallback_entity_extraction(self, text: str) -> Dict:
        """Fallback method for entity extraction if LLM fails"""
        # Simple regex patterns for entity extraction
        company_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b(?=\s+(?:Ltd|Inc|Corp|LLC|Group))'
        person_pattern = r'\b(?:Mr|Ms|Mrs|Dr)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b|\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        product_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b(?=\s+(?:Platform|Software|Tool|System|Solution))'
        
        companies = re.findall(company_pattern, text)
        people = re.findall(person_pattern, text)
        products = list(set(re.findall(product_pattern, text)))
        
        return {
            'companies': companies,
            'people': people,
            'products': products,
            'features': []
        }
    
    def generate_replacement_dict(self, entities: Dict) -> Dict:
        """Generate replacement mappings for entities"""
        replacement_dict = {}
        
        # Process companies
        for company in entities.get('companies', []):
            if company not in replacement_dict:
                replacement_dict[company] = self.generate_fictional_name(str(company))
        
        # Process people
        for person in entities.get('people', []):
            if person not in replacement_dict:
                replacement_dict[person] = self.generate_fictional_name(str(person))
        
        # Process products
        for product in entities.get('products', []):
            if product not in replacement_dict:
                replacement_dict[product] = self.generate_rephraser(str(product))
        
        # Process features
        for feature in entities.get('features', []):
            if feature not in replacement_dict:
                replacement_dict[feature] = self.generate_rephraser(str(feature))
        
        return replacement_dict
    
    def anonymize_text(self, text: str, replacement_dict: Dict) -> str:
        """Replace entities in text with fictional names"""
        # Sort by length to avoid partial replacements
        sorted_entities = sorted(replacement_dict.keys(), key=len, reverse=True)
        
        for entity in sorted_entities:
            replacement = replacement_dict[entity]
            # Use word boundaries to avoid partial matches
            text = re.sub(r'\b' + re.escape(entity) + r'\b', replacement, text)
        
        return text
    
    def process_file(self, file_path: str, anon_id: int):
        """Process a markdown file and create anonymized version"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print("File reading completed")

        # Extract entities
        entities = self.extract_entities(content)
        print("Entity extraction completed")
        
        # Generate replacement dictionary
        self.replacement_dict = self.generate_replacement_dict(entities)
        print("Replacement matrix construction completed")
        
        # Anonymize content
        anonymized_content = self.anonymize_text(content, self.replacement_dict)
        
        # Write to new file
        file_name = os.path.basename(file_path)
        output_path = "../markdowns/sales_case_studies/" f"anon_{anon_id}.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(anonymized_content)
        
        print(f"Anonymized file saved to: {output_path}")

def get_file_names(folder_path):
    """Return a list of file names (not directories) in the given folder."""
    return [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]


# Example usage
if __name__ == "__main__":
    anonymizer = Anonymizer()
    folder_path = "../markdowns/prop_sales_case_studies/"
    md_files = get_file_names(folder_path)
    id_num = 1
    for file in md_files:
        print("Processing file: ", file)
        file_path = folder_path + file
        anonymizer.process_file(file_path, id_num)
        id_num += 1
        print("\n")