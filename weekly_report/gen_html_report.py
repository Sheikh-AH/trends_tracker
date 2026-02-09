"""This module builds the HTML email for the weekly report."""

import base64


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

        # Check for markdown-style headings
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
            # Bold text as subheading
            html_parts.append(
                f'<p style="margin: 12px 0 4px 0; color: #0D3C81; font-weight: 600;">{line[2:-2]}</p>')
        elif line.startswith('- ') or line.startswith('* '):
            # Bullet points
            html_parts.append(
                f'<p style="margin: 4px 0 4px 16px; color: #334155;">• {line[2:]}</p>')
        else:
            # Regular paragraph
            html_parts.append(
                f'<p style="margin: 8px 0; color: #334155; line-height: 1.6;">{line}</p>')

    return ''.join(html_parts)


def build_weekly_report_email(report_data: dict, user_email: str, logo_url: str = None) -> str:
    """Builds the complete HTML email for the weekly report."""

    keyword_rows = ""
    for i, stat in enumerate(report_data["keywords"]):
        keyword_rows += build_keyword_row(stat, i)

    sentiment_table = build_sentiment_table(report_data["keywords"])

    # Format LLM summary with proper headings
    raw_summary = report_data.get("llm_summary") or ""
    llm_summary_html = format_llm_summary(raw_summary)

    totals = report_data["totals"]

    if logo_url:
        logo_section = f'<img src="{logo_url}" alt="TrendFunnel" style="height: 48px; width: auto;"><span style="font-size: 24px; font-weight: 700; color: #0D47A1; margin-left: 12px; font-family: Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif; vertical-align: middle;">TrendFunnel</span>'
    else:
        logo_section = '<span style="font-size: 24px; font-weight: 700; color: #0D47A1; font-family: Ubuntu, -apple-system, BlinkMacSystemFont, sans-serif;">TrendFunnel</span>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Georgia', 'Times New Roman', serif; background-color: #f1f5f9; -webkit-font-smoothing: antialiased;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f1f5f9;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 640px; background-color: #ffffff; border: 1px solid #e2e8f0;">
                        
                        <!-- Header -->
                        <tr>
                            <td style="padding: 32px 40px; border-bottom: 3px solid #0D47A1;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td>{logo_section}</td>
                                        <td style="text-align: right; vertical-align: middle;">
                                            <span style="font-size: 12px; color: #64748b; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Weekly Report</span>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Title -->
                        <tr>
                            <td style="padding: 40px 40px 24px 40px;">
                                <h1 style="margin: 0 0 8px 0; color: #0D3C81; font-size: 28px; font-weight: 400; line-height: 1.3;">Weekly Trends Analysis</h1>
                                <p style="margin: 0; color: #64748b; font-size: 14px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">A summary of keyword activity and sentiment trends from the past week</p>
                            </td>
                        </tr>
                        
                        <!-- Executive Summary -->
                        <tr>
                            <td style="padding: 0 40px 32px 40px;">
                                <h2 style="margin: 0 0 16px 0; color: #0D47A1; font-size: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Executive Summary</h2>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 20px; background-color: #f8fafc; border-left: 4px solid #1976D2; width: 33%;">
                                            <div style="font-size: 32px; font-weight: 300; color: #0D3C81; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">{totals["posts_24h"]:,}</div>
                                            <div style="font-size: 12px; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Posts (24h)</div>
                                        </td>
                                        <td style="width: 16px;"></td>
                                        <td style="padding: 20px; background-color: #f8fafc; border-left: 4px solid #1565C0; width: 33%;">
                                            <div style="font-size: 32px; font-weight: 300; color: #0D3C81; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">{totals["posts_7d"]:,}</div>
                                            <div style="font-size: 12px; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Posts (7 days)</div>
                                        </td>
                                        <td style="width: 16px;"></td>
                                        <td style="padding: 20px; background-color: #f8fafc; border-left: 4px solid #0D47A1; width: 33%;">
                                            <div style="font-size: 32px; font-weight: 300; color: #0D3C81; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">{totals["avg_positive_sentiment"]}%</div>
                                            <div style="font-size: 12px; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Avg. Positive Sentiment</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Keyword Performance -->
                        <tr>
                            <td style="padding: 0 40px 32px 40px;">
                                <h2 style="margin: 0 0 16px 0; color: #0D47A1; font-size: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Keyword Performance</h2>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse: collapse; border: 1px solid #e2e8f0;">
                                    <thead>
                                        <tr style="background-color: #0D47A1;">
                                            <th style="padding: 12px 16px; text-align: left; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Keyword</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">24h</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">7 Days</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Positive</th>
                                            <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #ffffff; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Trending (vs Last Week)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {keyword_rows}
                                    </tbody>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Sentiment Distribution -->
                        <tr>
                            <td style="padding: 0 40px 32px 40px;">
                                <h2 style="margin: 0 0 16px 0; color: #0D47A1; font-size: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Sentiment Distribution</h2>
                                {sentiment_table}
                            </td>
                        </tr>
                        
                        <!-- Analysis -->
                        <tr>
                            <td style="padding: 0 40px 32px 40px;">
                                <h2 style="margin: 0 0 16px 0; color: #0D47A1; font-size: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">Analysis</h2>
                                <div style="background-color: #f8fafc; padding: 24px; border-left: 4px solid #1976D2;">
                                    {llm_summary_html}
                                </div>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 24px 40px; background-color: #0D3C81;">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="font-size: 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                                            <p style="margin: 0 0 8px 0; color: #ffffff; font-weight: 600;">Trend Funnel</p>
                                            <p style="margin: 0; color: #94a3b8;">This report was generated automatically for {user_email}</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html
