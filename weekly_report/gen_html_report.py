"""This module builds the HTML email for the weekly report."""


def build_keyword_row(keyword_stat: dict) -> str:
    """Builds a single row for the keyword performance table."""
    trend = keyword_stat["trend"]
    trend_color = "#10b981" if trend["direction"] == "up" else "#ef4444" if trend["direction"] == "down" else "#6b7280"

    google_trends = keyword_stat["google_trends"]
    google_trends_display = f"{google_trends}/100" if google_trends is not None else "N/A"

    return f"""
    <tr>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; font-weight: 600; color: #0085ff;">#{keyword_stat["keyword"]}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: center;">{keyword_stat["posts_24h"]:,}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: center;">{keyword_stat["posts_7d"]:,}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: center;">{keyword_stat["sentiment"]["positive"]}% 😊</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: center;">{google_trends_display}</td>
        <td style="padding: 12px 16px; border-bottom: 1px solid #e5e7eb; text-align: center; color: {trend_color}; font-weight: 600;">{trend["symbol"]} {trend["percent"]}%</td>
    </tr>
    """


def build_sentiment_section(keyword_stats: list[dict]) -> str:
    """Builds the sentiment breakdown section."""
    sentiment_html = ""

    for stat in keyword_stats:
        sentiment = stat["sentiment"]
        sentiment_html += f"""
        <div style="margin-bottom: 16px;">
            <div style="font-weight: 600; color: #333; margin-bottom: 8px;">#{stat["keyword"]}</div>
            <div style="background-color: #f3f4f6; border-radius: 8px; overflow: hidden; height: 24px; display: flex;">
                <div style="background-color: #10b981; width: {sentiment["positive"]}%; height: 100%;"></div>
                <div style="background-color: #6b7280; width: {sentiment["neutral"]}%; height: 100%;"></div>
                <div style="background-color: #ef4444; width: {sentiment["negative"]}%; height: 100%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666; margin-top: 4px;">
                <span>😊 {sentiment["positive"]}%</span>
                <span>😐 {sentiment["neutral"]}%</span>
                <span>😞 {sentiment["negative"]}%</span>
            </div>
        </div>
        """

    return sentiment_html


def build_weekly_report_email(report_data: dict, user_email: str) -> str:
    """Builds the complete HTML email for the weekly report."""

    # Build keyword rows
    keyword_rows = ""
    for stat in report_data["keywords"]:
        keyword_rows += build_keyword_row(stat)

    # Build sentiment section
    sentiment_section = build_sentiment_section(report_data["keywords"])

    # LLM summary
    llm_summary = report_data.get(
        "llm_summary") or "No AI insights available for this week."

    # Totals
    totals = report_data["totals"]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f0f2f5;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f0f2f5;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #0085ff 0%, #00c6ff 100%); padding: 32px; text-align: center; border-radius: 16px 16px 0 0;">
                                <div style="font-size: 48px; margin-bottom: 8px;">📊</div>
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">Your Weekly Trends Report</h1>
                                <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.8); font-size: 14px;">Here's what happened with your keywords this week</p>
                            </td>
                        </tr>
                        
                        <!-- Overview Stats -->
                        <tr>
                            <td style="padding: 24px 32px;">
                                <h2 style="margin: 0 0 16px 0; color: #333; font-size: 18px; font-weight: 600;">📈 Overview</h2>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="text-align: center; padding: 16px; background-color: #f8f9fa; border-radius: 12px; width: 33%;">
                                            <div style="font-size: 28px; font-weight: 700; color: #0085ff;">{totals["posts_24h"]:,}</div>
                                            <div style="font-size: 12px; color: #666; margin-top: 4px;">Posts (24h)</div>
                                        </td>
                                        <td style="width: 12px;"></td>
                                        <td style="text-align: center; padding: 16px; background-color: #f8f9fa; border-radius: 12px; width: 33%;">
                                            <div style="font-size: 28px; font-weight: 700; color: #0085ff;">{totals["posts_7d"]:,}</div>
                                            <div style="font-size: 12px; color: #666; margin-top: 4px;">Posts (7d)</div>
                                        </td>
                                        <td style="width: 12px;"></td>
                                        <td style="text-align: center; padding: 16px; background-color: #f8f9fa; border-radius: 12px; width: 33%;">
                                            <div style="font-size: 28px; font-weight: 700; color: #10b981;">{totals["avg_positive_sentiment"]}%</div>
                                            <div style="font-size: 12px; color: #666; margin-top: 4px;">Avg Positive</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Keyword Performance Table -->
                        <tr>
                            <td style="padding: 0 32px 24px 32px;">
                                <h2 style="margin: 0 0 16px 0; color: #333; font-size: 18px; font-weight: 600;">🔑 Keyword Performance</h2>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden;">
                                    <tr style="background-color: #f8f9fa;">
                                        <th style="padding: 12px 16px; text-align: left; font-size: 12px; color: #666; font-weight: 600;">KEYWORD</th>
                                        <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">24H</th>
                                        <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">7D</th>
                                        <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">SENTIMENT</th>
                                        <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">GOOGLE</th>
                                        <th style="padding: 12px 16px; text-align: center; font-size: 12px; color: #666; font-weight: 600;">TREND</th>
                                    </tr>
                                    {keyword_rows}
                                </table>
                            </td>
                        </tr>
                        
                        <!-- Sentiment Breakdown -->
                        <tr>
                            <td style="padding: 0 32px 24px 32px;">
                                <h2 style="margin: 0 0 16px 0; color: #333; font-size: 18px; font-weight: 600;">💭 Sentiment Breakdown</h2>
                                {sentiment_section}
                            </td>
                        </tr>
                        
                        <!-- AI Insights -->
                        <tr>
                            <td style="padding: 0 32px 24px 32px;">
                                <h2 style="margin: 0 0 16px 0; color: #333; font-size: 18px; font-weight: 600;">🤖 AI Insights</h2>
                                <div style="background-color: #f0f9ff; border-radius: 12px; padding: 20px; border-left: 4px solid #0085ff;">
                                    <p style="margin: 0; color: #333; font-size: 14px; line-height: 1.6;">{llm_summary}</p>
                                </div>
                            </td>
                        </tr>
                        
                        <!-- CTA Button -->
                        <tr>
                            <td style="padding: 0 32px 32px 32px; text-align: center;">
                                <a href="https://your-dashboard-url.com" style="display: inline-block; background: linear-gradient(135deg, #0085ff 0%, #00c6ff 100%); color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 25px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 12px rgba(0, 133, 255, 0.4);">
                                    📊 View Full Dashboard
                                </a>
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
