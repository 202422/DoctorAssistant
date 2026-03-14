# DoctorAssistant


Doctor Assistant is a **Multi-Agent System (MAS)** built with **LangGraph/LangChain** that provides
AI-powered medical symptom analysis and preliminary diagnosis. It orchestrates multiple specialized agents working together to analyze patient symptoms, retrieve medical history, and generate
comprehensive medical assessments.



![](medical_multiagent_graph.png)

## Video Demo

[Watch the demo video](https://drive.google.com/file/d/1xdEF-TDnVvLbRdakQA4jO5fB_Z5fvROG/view?usp=sharing)

<h2>Tech Stack</h2>

<table>
<tr>
<th>Category</th>
<th>Technologies</th>
<th>Purpose</th>
</tr>

<tr>
<td rowspan="4" align="center"><b>Core Stack</b></td>
<td>Python 3.12</td>
<td>Primary programming language</td>
</tr>
<tr>
<td>LangGraph</td>
<td>Multi-agent orchestration (StateGraph, conditional edges, checkpointing)</td>
</tr>
<tr>
<td>LangChain (Core, OpenAI, Community, HuggingFace)</td>
<td>LLM integration, prompts, tools, and RAG pipelines</td>
</tr>
<tr>
<td>Gradio</td>
<td>Chat-based web interface</td>
</tr>

<tr>
<td rowspan="3" align="center"><b>LLM Models</b></td>
<td>GPT-5.2</td>
<td>Used by most agents (Planner, Supervisor, Patient Data, Cardiovascular, Neurological, Pharmacy Finder)</td>
</tr>
<tr>
<td>GPT-4.1-nano</td>
<td>Used by the Synthesis agent</td>
</tr>
<tr>
<td>OpenAI-compatible proxy</td>
<td>Model access via custom endpoint</td>
</tr>

<tr>
<td rowspan="3" align="center"><b>RAG / Vector Search</b></td>
<td>FAISS</td>
<td>Vector similarity search over medical documents</td>
</tr>
<tr>
<td>HuggingFace Embeddings (all-MiniLM-L6-v2)</td>
<td>Local embedding generation</td>
</tr>
<tr>
<td>PyPDF</td>
<td>PDF loading and parsing</td>
</tr>

<tr>
<td rowspan="2" align="center"><b>MCP Integrations</b></td>
<td>Neon PostgreSQL MCP (Smithery)</td>
<td>Patient records database queries</td>
</tr>
<tr>
<td>Google Maps MCP (Smithery)</td>
<td>Pharmacy location search</td>
</tr>

<tr>
<td rowspan="3" align="center"><b>External APIs</b></td>
<td>Nominatim (OpenStreetMap)</td>
<td>Address geocoding</td>
</tr>
<tr>
<td>OSRM</td>
<td>Real-world routing and distance calculation</td>
</tr>
<tr>
<td>LangSmith</td>
<td>LLM tracing and observability</td>
</tr>

<tr>
<td rowspan="3" align="center"><b>Database</b></td>
<td>Neon PostgreSQL (Cloud)</td>
<td>Patient data storage</td>
</tr>
<tr>
<td>SQLAlchemy</td>
<td>ORM and database abstraction</td>
</tr>
<tr>
<td>psycopg2-binary / asyncpg</td>
<td>PostgreSQL drivers</td>
</tr>

<tr>
<td rowspan="2" align="center"><b>HTTP Clients</b></td>
<td>httpx</td>
<td>Async HTTP client for MCP communication</td>
</tr>
<tr>
<td>requests</td>
<td>External API calls</td>
</tr>

<tr>
<td rowspan="2" align="center"><b>Data Validation & Config</b></td>
<td>Pydantic</td>
<td>State schemas, structured LLM outputs, and tool validation</td>
</tr>
<tr>
<td>python-dotenv</td>
<td>Environment variable management</td>
</tr>

</table>
