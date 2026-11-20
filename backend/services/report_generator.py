import os
from jinja2 import Environment, FileSystemLoader
from backend.models.schemas import AnalysisResult

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

class ReportGenerator:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)

    def render_summary_html(self, analysis: AnalysisResult) -> str:
        template = self.env.get_template("summary.html")
        return template.render(analysis=analysis)

    def render_quick_actions_html(self, analysis: AnalysisResult) -> str:
        template = self.env.get_template("quick_actions.html")
        return template.render(analysis=analysis)

    def render_action_items_html(self, analysis: AnalysisResult) -> str:
        template = self.env.get_template("action_items.html")
        return template.render(analysis=analysis)

    def render_jd_comparison_html(self, analysis: AnalysisResult) -> str:
        template = self.env.get_template("jd_comparison.html")
        return template.render(analysis=analysis)

    def render_full_report_html(self, analysis: AnalysisResult) -> str:
        """Combines all templates into a multi-page document separated by page-breaks."""
        summary = self.render_summary_html(analysis)
        actions = self.render_action_items_html(analysis)
        playbook = self.render_quick_actions_html(analysis)
        jd_comp = self.render_jd_comparison_html(analysis) if analysis.jd_comparison else ""

        full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 15mm; }}
  .page-break {{ page-break-after: always; }}
</style>
</head>
<body>
  {summary}
  <div class="page-break"></div>
  {actions}
  <div class="page-break"></div>
  {playbook}
  {"<div class='page-break'></div>" + jd_comp if jd_comp else ""}
</body>
</html>
"""
        return full_html

report_generator = ReportGenerator()
