"""Generate a Japanese monthly sales report PDF from a sales CSV file.

Usage:
    python generate_sales_report.py <input_csv> <output_pdf> [--title "2025年1月 売上レポート"]

CSV must have columns: 日付,部門,商品名,販売数量,単価,売上金額,顧客区分,地域
"""
import argparse
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.legends import Legend

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

HEADER_BG = colors.HexColor("#16213e")
ROW_ALT_BG = colors.HexColor("#f2f4f8")
CHART_COLORS = [colors.HexColor(c) for c in [
    "#16213e", "#0f3460", "#533483", "#e94560", "#ff6b6b",
    "#f39c12", "#27ae60", "#2980b9", "#8e44ad", "#c0392b",
]]


def register_fonts():
    pdfmetrics.registerFont(
        TTFont("NotoSansJP", str(FONTS_DIR / "NotoSansJP-Regular.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("NotoSansJP-Bold", str(FONTS_DIR / "NotoSansJP-Bold.ttf"))
    )


def yen(v):
    return f"¥{v:,.0f}"


def department_bar_chart(dept_summary):
    drawing = Drawing(450, 220)
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 60
    chart.width = 370
    chart.height = 140
    chart.data = [list(dept_summary["売上金額"])]
    for i in range(len(dept_summary)):
        chart.bars[(0, i)].fillColor = CHART_COLORS[i % len(CHART_COLORS)]
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontName = "NotoSansJP"
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.labelTextFormat = lambda v: f"{v:,.0f}"
    chart.categoryAxis.categoryNames = list(dept_summary.index)
    chart.categoryAxis.labels.fontName = "NotoSansJP"
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.angle = 30
    chart.categoryAxis.labels.dx = -6
    chart.categoryAxis.labels.dy = -12
    drawing.add(chart)
    return drawing


def product_pie_chart(product_summary):
    drawing = Drawing(450, 220)
    pie = Pie()
    pie.x = 120
    pie.y = 20
    pie.width = 160
    pie.height = 160
    pie.data = list(product_summary["売上金額"])
    pie.labels = None
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    for i in range(len(pie.data)):
        pie.slices[i].fillColor = CHART_COLORS[i % len(CHART_COLORS)]

    legend = Legend()
    legend.x = 305
    legend.y = 175
    legend.dx = 8
    legend.dy = 8
    legend.fontName = "NotoSansJP"
    legend.fontSize = 7.5
    legend.alignment = "left"
    legend.columnMaximum = 10
    legend.colorNamePairs = [
        (CHART_COLORS[i % len(CHART_COLORS)], name)
        for i, name in enumerate(product_summary.index)
    ]

    drawing.add(pie)
    drawing.add(legend)
    return drawing


def styled_table(data, col_widths, num_cols_right_align):
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "NotoSansJP"),
        ("FONTNAME", (0, 0), (-1, 0), "NotoSansJP-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for col in num_cols_right_align:
        style.append(("ALIGN", (col, 1), (col, -1), "RIGHT"))
    for row in range(1, len(data)):
        if row % 2 == 0:
            style.append(("BACKGROUND", (0, row), (-1, row), ROW_ALT_BG))
    table.setStyle(TableStyle(style))
    return table


def build_report(csv_path, pdf_path, title):
    register_fonts()
    df = pd.read_csv(csv_path)

    title_style = ParagraphStyle(
        "Title", fontName="NotoSansJP-Bold", fontSize=20, leading=26,
        spaceAfter=6, textColor=colors.HexColor("#1a1a2e"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", fontName="NotoSansJP", fontSize=10, leading=14,
        spaceAfter=18, textColor=colors.HexColor("#555555"),
    )
    heading_style = ParagraphStyle(
        "Heading", fontName="NotoSansJP-Bold", fontSize=14, leading=18,
        spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "Body", fontName="NotoSansJP", fontSize=10, leading=15,
    )

    story = [
        Paragraph(title, title_style),
        Paragraph(
            f"対象期間: {df['日付'].min()} 〜 {df['日付'].max()}",
            subtitle_style,
        ),
    ]

    # 概要
    total_amount = df["売上金額"].sum()
    total_qty = df["販売数量"].sum()
    n_days = df["日付"].nunique()
    n_departments = df["部門"].nunique()
    n_products = df["商品名"].nunique()
    avg_daily = total_amount / n_days
    top_department = df.groupby("部門")["売上金額"].sum().idxmax()
    top_product = df.groupby("商品名")["売上金額"].sum().idxmax()

    story.append(Paragraph("概要", heading_style))
    overview_data = [
        ["項目", "値"],
        ["総売上金額", yen(total_amount)],
        ["総販売数量", f"{total_qty:,} 個"],
        ["集計日数", f"{n_days} 日"],
        ["1日あたり平均売上", yen(avg_daily)],
        ["部門数", f"{n_departments} 部門"],
        ["取扱商品数", f"{n_products} 品目"],
        ["最多売上部門", top_department],
        ["最多売上商品", top_product],
    ]
    story.append(styled_table(overview_data, [70 * mm, 90 * mm], [1]))

    # 部門別売上
    story.append(Paragraph("部門別売上", heading_style))
    dept_summary = (
        df.groupby("部門")
        .agg(売上金額=("売上金額", "sum"), 販売数量=("販売数量", "sum"))
        .sort_values("売上金額", ascending=False)
    )
    dept_summary["構成比"] = dept_summary["売上金額"] / total_amount * 100

    dept_data = [["部門", "売上金額", "販売数量", "構成比"]]
    for name, row in dept_summary.iterrows():
        dept_data.append([
            name,
            yen(row["売上金額"]),
            f"{row['販売数量']:,} 個",
            f"{row['構成比']:.1f}%",
        ])
    dept_data.append([
        "合計",
        yen(dept_summary["売上金額"].sum()),
        f"{dept_summary['販売数量'].sum():,} 個",
        "100.0%",
    ])
    story.append(styled_table(dept_data, [55 * mm, 40 * mm, 35 * mm, 30 * mm], [1, 2, 3]))
    story.append(Spacer(1, 12))
    story.append(department_bar_chart(dept_summary))

    # 商品別ランキング
    story.append(PageBreak())
    story.append(Paragraph("商品別ランキング", heading_style))
    story.append(Paragraph("売上金額の上位10商品を掲載しています。", body_style))
    story.append(Spacer(1, 6))

    product_summary = (
        df.groupby("商品名")
        .agg(売上金額=("売上金額", "sum"), 販売数量=("販売数量", "sum"))
        .sort_values("売上金額", ascending=False)
        .head(10)
    )

    rank_data = [["順位", "商品名", "売上金額", "販売数量"]]
    for i, (name, row) in enumerate(product_summary.iterrows(), start=1):
        rank_data.append([
            f"{i}",
            name,
            yen(row["売上金額"]),
            f"{row['販売数量']:,} 個",
        ])
    rank_data.append([
        "",
        "上位10商品 合計",
        yen(product_summary["売上金額"].sum()),
        f"{product_summary['販売数量'].sum():,} 個",
    ])
    story.append(styled_table(rank_data, [15 * mm, 75 * mm, 40 * mm, 30 * mm], [2, 3]))
    story.append(Spacer(1, 12))
    story.append(product_pie_chart(product_summary))

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=title,
    )
    doc.build(story)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv")
    parser.add_argument("output_pdf")
    parser.add_argument("--title", default="月次売上レポート")
    args = parser.parse_args()
    build_report(args.input_csv, args.output_pdf, args.title)
    print(f"生成しました: {args.output_pdf}")


if __name__ == "__main__":
    main()
