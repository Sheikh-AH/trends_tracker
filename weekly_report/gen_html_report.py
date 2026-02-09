"""This module builds the HTML email for the weekly report."""

import os


def get_template_path() -> str:
    """Returns the absolute path to the template file."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.html")


def load_template() -> str:
    """Loads the HTML template from file."""
    with open(get_template_path(), "r", encoding="utf-8") as f:
        return f.read()


def build_keyword_row(keyword_stat: dict, index: int) -> str:
    """Builds a single row for the keyword performance table."""
    trend = keyword_stat["trend"]
    trend_text = f"{trend['direction'].capitalize()} {trend['percent']}%"

    return f"""
    <tr style="background-color: {'#f8fafc' if index % 2 == 0 else '#ffffff'};">
        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; color: #0D47A1; font-weight: 500;">#{keyword_stat["keyword"]}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{keyword_stat["posts_24h"]:,}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{keyword_stat["posts_7d"]:,}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{keyword_stat["sentiment"]["positive"]}%</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{trend_text}</td>
    </tr>
    """


def build_sentiment_table(keyword_stats: list[dict]) -> str:
    """Builds a clean sentiment breakdown table."""
    rows = ""
    for i, stat in enumerate(keyword_stats):
        sentiment = stat["sentiment"]
        bg_color = '#f8fafc' if i % 2 == 0 else '#ffffff'
        rows += f"""
        <tr style="background-color: {bg_color};">
            <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; color: #0D47A1; font-weight: 500;">#{stat["keyword"]}</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{sentiment["positive"]}%</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{sentiment["neutral"]}%</td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #e2e8f0; text-align: center; color: #334155;">{sentiment["negative"]}%</td>
        </tr>
        """

    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; border: 1px solid #e2e8f0;">
        <thead>
            <tr style="background-color: #0D47A1;">
                <th style="padding: 12px 16px; text-align: left; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Keyword</th>
                <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Positive</th>
                <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Neutral</th>
                <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Negative</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def format_llm_summary(summary: str) -> str:
    """Formats the LLM summary with proper HTML structure for headings and paragraphs."""
    if not summary:
        return "<p>No analysis available for this reporting period.</p>"

    lines = summary.strip().split('\n')
    html_parts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('### '):
            html_parts.append(
                f'<h4 style="margin: 16px 0 8px 0; color: #0D47A1; font-size: 14px; font-weight: 600;">{line[4:]}</h4>')
        elif line.startswith('## '):
            html_parts.append(
                f'<h3 style="margin: 16px 0 8px 0; color: #0D47A1; font-size: 16px; font-weight: 600;">{line[3:]}</h3>')
        elif line.startswith('# '):
            html_parts.append(
                f'<h3 style="margin: 16px 0 8px 0; color: #0D47A1; font-size: 18px; font-weight: 600;">{line[2:]}</h3>')
        elif line.startswith('**') and line.endswith('**'):
            html_parts.append(
                f'<p style="margin: 12px 0 4px 0; color: #0D3C81; font-weight: 600;">{line[2:-2]}</p>')
        elif line.startswith('- ') or line.startswith('* '):
            html_parts.append(
                f'<p style="margin: 4px 0 4px 16px; color: #334155;">• {line[2:]}</p>')
        else:
            html_parts.append(
                f'<p style="margin: 8px 0; color: #334155; line-height: 1.6;">{line}</p>')

    return ''.join(html_parts)


def build_weekly_report_email(report_data: dict, user_email: str, logo_url: str = None) -> str:
    """Builds the complete HTML email for the weekly report."""

    keyword_rows = ""
    for i, stat in enumerate(report_data["keywords"]):
        keyword_rows += build_keyword_row(stat, i)

    sentiment_table = build_sentiment_table(report_data["keywords"])

    raw_summary = report_data.get("llm_summary") or ""
    llm_summary_html = format_llm_summary(raw_summary)

    totals = report_data["totals"]

    if logo_url:
        logo_section = f'<img src="{logo_url}" alt="TrendFunnel" style="height: 48px; width: auto;"><span style="font-size: 24px; font-weight: 700; color: #0D47A1; margin-left: 12px; font-family: Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif; vertical-align: middle;">TrendFunnel</span>'
    else:
        logo_section = '<span style="font-size: 24px; font-weight: 700; color: #0D47A1; font-family: Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif;">TrendFunnel</span>'

    template = load_template()

    html = template.replace("{{logo_section}}", logo_section)
    html = html.replace("{{posts_24h}}", f"{totals['posts_24h']:,}")
    html = html.replace("{{posts_7d}}", f"{totals['posts_7d']:,}")
    html = html.replace("{{avg_positive_sentiment}}",
                        str(totals["avg_positive_sentiment"]))
    html = html.replace("{{keyword_rows}}", keyword_rows)
    html = html.replace("{{sentiment_table}}", sentiment_table)
    html = html.replace("{{llm_summary_html}}", llm_summary_html)
    html = html.replace("{{user_email}}", user_email)

    return html
