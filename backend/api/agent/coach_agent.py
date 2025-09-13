import dspy
from pydantic import BaseModel, Field
from typing import List, Optional
from model.context_model import ( ConversationAnalysis, ClientAgentContextModel, CoachAgentProblemAnalysis, CoachAgentSolutionAnalysis )
from .prompt import (get_coach_agent_classification_prompt, get_coach_agent_behavioral_cue_prompt, get_coach_agent_risk_prompt)
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from util.inference_service import ( get_llm_output )
from util.db_service import (get_solutions_to_objections)
import json

class CoachAgent:
    def __init__(self):
        self.classification = ""

    def classify_response(self, client_agent_context: ClientAgentContextModel):
        classification_prompt = get_coach_agent_classification_prompt(client_agent_context)
        classification_output = ""
        print("coach classification start")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_output, classification_prompt)
            try:
                classification_output = future.result(timeout=45)
                # print("coach agent classification response", classification_output)
            except FutureTimeoutError:
                return "Prediction timed out after 45 seconds"
            except Exception as e:
                return f"Error during prediction: {e}"

        # Add client response to history
        return classification_output

    def extract_behavioral_queue(self, client_agent_context: ClientAgentContextModel):
        behavioral_cue_prompt = get_coach_agent_behavioral_cue_prompt(client_agent_context)
        output = ""
        print("CoachAgent-behavioral cues start")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_output, behavioral_cue_prompt)
            try:
                output = future.result(timeout=45)
                # print("response", json.dumps(output, indent=2, default=str))
            except FutureTimeoutError:
                return "Prediction timed out after 45 seconds"
            except Exception as e:
                return f"Error during prediction: {e}"

        # Add client response to history
        return output

    def extract_risks(self, client_agent_context: ClientAgentContextModel):
        risk_analysis_prompt = get_coach_agent_risk_prompt(client_agent_context)
        output = ""
        print("CoachAgent-risk analysis start")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_output, risk_analysis_prompt)
            try:
                output = future.result(timeout=45)
                # print("response", json.dumps(output, indent=2, default=str))
            except FutureTimeoutError:
                return "Prediction timed out after 45 seconds"
            except Exception as e:
                return f"Error during prediction: {e}"

        # Add client response to history
        return output

    def get_solution_techniques(self, coach_agent_problem_analysis: CoachAgentProblemAnalysis, coach_solution_analysis: CoachAgentSolutionAnalysis):
        print("CoachAgent-solution retrieval start")
        sol_techinques = get_solutions_to_objections(coach_agent_problem_analysis, coach_solution_analysis)
        print(sol_techinques)
        return sol_techinques

    def generate_report(self, coach_agent_problem_analysis: CoachAgentProblemAnalysis, 
                        coach_solution_analysis: CoachAgentSolutionAnalysis, client_agent_context: ClientAgentContextModel):
        print("CoachAgent-solution retrieval start")
        sol_techinques = get_solutions_to_objections(coach_agent_problem_analysis, coach_solution_analysis)
        print(sol_techinques)
        return sol_techinques