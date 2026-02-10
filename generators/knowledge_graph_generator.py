from langchain_groq import ChatGroq
from langchain.messages import SystemMessage, HumanMessage
import os
from typing import Optional
import tiktoken


class FlowchartGenerator:
    """Generate flowchart summary of lecture"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found")
        
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=4000,
        )
        
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None
    
    def count_tokens(self, text: str) -> int:
        if self.encoding:
            return len(self.encoding.encode(text))
        return len(text) // 4
    
    def generate(
        self,
        content: str,
        course_code: str = "",
        title: str = ""
    ) -> str:
        """
        Generate flowchart as Mermaid syntax
        
        Returns:
            Mermaid flowchart code (text)
        """
        
        print(f"📊 Generating flowchart...")
        
        tokens = self.count_tokens(content)
        print(f"   Content tokens: {tokens}")
        
        
        flowchart = self._generate_flowchart(content, course_code, title)
        
        print(f"✅ Flowchart generated")
        
        return flowchart
    
    
    def _generate_flowchart(self, content: str, course: str, title: str) -> str:
        """Generate Mermaid flowchart"""
        
        prompt = f"""Create a flowchart that SUMMARIZES the lecture content with main topics and key points.

Course: {course}
Title: {title}

CONTENT:
{content}

Create a Mermaid flowchart showing:
1. Lecture title at top
2. Each MAIN TOPIC as a node
3. KEY POINTS under each topic as sub-nodes
4. Clear hierarchy showing topic → points

EXAMPLE STRUCTURE:

flowchart TD
    Start(["{title}"])
    
    Start --> T1["Topic 1: Machine Learning"]
    T1 --> P1["• Learns from data"]
    T1 --> P2["• No explicit programming"]
    T1 --> P3["• Improves with experience"]
    
    Start --> T2["Topic 2: Supervised Learning"]
    T2 --> P4["• Uses labeled data"]
    T2 --> P5["• Examples: spam detection, image classification"]
    T2 --> P6["• Requires training examples"]
    
    Start --> T3["Topic 3: Applications"]
    T3 --> P7["• Voice assistants"]
    T3 --> P8["• Recommendation systems"]
    T3 --> P9["• Medical diagnosis"]

REQUIREMENTS:
- Extract ACTUAL content from the lecture
- Include ALL main topics covered
- List 2-4 key points per topic
- Use actual terminology from the content
- Keep labels concise (5-8 words max)
- Maximum 20 nodes total
- Show content hierarchy clearly

FORMATTING:
- Main topics: ["Topic: Name"]
- Key points: ["• Point description"]
- Keep it readable and clear

Return ONLY the Mermaid code, starting with "flowchart TD"
DO NOT include markdown code blocks."""
        
        messages = [
            SystemMessage(content="You are an expert at creating clear flowcharts."),
            HumanMessage(content=prompt)
        ]
        
        response = self.llm.invoke(messages)
        
        # Extract mermaid code
        mermaid = response.content.strip()
        
        # Remove markdown code blocks if present
        import re
        mermaid = re.sub(r'```mermaid\s*', '', mermaid)
        mermaid = re.sub(r'```\s*', '', mermaid)
        
        return mermaid.strip()
    
    def save_mermaid(self, flowchart: str, path: str):
        """Save Mermaid code to file"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(flowchart)
        print(f"💾 Mermaid saved: {path}")
    
    def generate_html(
        self,
        content: str,
        output_path: str,
        course_code: str = "",
        title: str = ""
    ):
        """Generate flowchart and create HTML visualization"""
        
        # Generate flowchart
        flowchart = self.generate(content, course_code, title)
        
        # Save Mermaid code
        mermaid_path = output_path.replace('.html', '.mmd')
        self.save_mermaid(flowchart, mermaid_path)
        
        # Create HTML
        print(f"📄 Creating HTML visualization...")
        html = self._create_html(flowchart, course_code, title)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Flowchart HTML: {output_path}")
        print(f"✅ Mermaid code: {mermaid_path}")
        
        return output_path
    
    def _create_html(self, mermaid_code: str, course: str, title: str) -> str:
        """Create HTML with Mermaid rendering"""
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Flowchart: {title}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #1565c0;
            margin: 0 0 10px 0;
        }}
        .course {{
            color: #666;
            font-size: 14px;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        .mermaid {{
            text-align: center;
        }}
        .instructions {{
            margin-top: 20px;
            padding: 15px;
            background: #e3f2fd;
            border-left: 4px solid #1565c0;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Lecture Flowchart</h1>
        <h2>{title}</h2>
        <p class="course">Course: {course}</p>
    </div>
    
    <div class="container">
        <div class="mermaid">
{mermaid_code}
        </div>
    </div>
    
    <div class="instructions">
        <h3>📊 How to Read This Flowchart:</h3>
        <ul>
            <li><strong>Top box</strong> = Lecture title</li>
            <li><strong>Topic boxes</strong> = Main topics covered</li>
            <li><strong>Bullet points</strong> = Key points under each topic</li>
            <li><strong>Follow connections</strong> to see topic hierarchy</li>
        </ul>
    </div>
    
    <script>
        mermaid.initialize({{ 
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }}
        }});
    </script>
</body>
</html>"""


def read_text_file(path: str) -> str:
    """Read lecture content from a .txt file safely."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Lecture file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        raise ValueError(f"Lecture file is empty: {path}")

    return content

# ============================================
# USAGE EXAMPLE
# ============================================

# if __name__ == "__main__":
#     from dotenv import load_dotenv
#     load_dotenv()
    
#     content =read_text_file("1_introduction_to_infosec_text.txt")
    
#     generator = FlowchartGenerator()
    
#     print("="*80)
#     print("GENERATING LECTURE FLOWCHART")
#     print("="*80)
    
#     generator.generate_html(
#         content=content,
#         output_path="lecture_flowchart.html",
#         course_code="IS101",
#         title="Introduction to InfoSecurity"
#     )
    
#     print("\n" + "="*80)
#     print("✅ Complete!")
#     print("="*80)
#     print("\nGenerated files:")
#     print("  📊 lecture_flowchart.html - Interactive flowchart")
#     print("  📝 lecture_flowchart.mmd - Mermaid code")
#     print("\nOpen the HTML file in your browser to view! 🎉")