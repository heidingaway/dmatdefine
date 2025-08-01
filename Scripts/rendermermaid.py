import execjs
# Define the Mermaid code for the flowchart
mermaid_code = """
graph TD;
    A[Start] --> B[Decision]
    B -- Yes --> C[Option 1]
    B -- No --> D[Option 2]
    C --> E[End]
    D --> E
    E[End] --> F[End]
"""
# Create an ExecJS context
context = execjs.compile("""
    var mermaid = require('mermaid');
    mermaid.initialize({startOnLoad:true});
    function renderMermaid(mermaidCode) {
        mermaid.mermaidAPI.render('mermaid', mermaidCode, function(svgCode, bindFunctions) {
            document.getElementById('diagram').innerHTML = svgCode;
        });
    }
""")
# Render the flowchart
context.call("renderMermaid", mermaid_code)
# Print the Mermaid code for reference
print(mermaid_code)