from pydantic import BaseModel, ConfigDict

TEMPLATES = {
    "python": "print('Hello World')",
    "java": "public class Main {\n public static void main(String[] args) {\n System.out.println(\"Hello World\"); \n} \n}",
    "cpp": "#include <iostream>\nusing namespace std;\nint main() { cout << \"Hello World\"; return 0; }"
}

class CodeSessionResponse(BaseModel):
   model_config = ConfigDict(from_attributes=True)

   session_id : str
   status : str
   # language : str
   # template_code : str

class CodeSessionRequest(BaseModel):
    language : str

class CodeSessionUpdateRequest(BaseModel):
    language : str
    source_code: str









