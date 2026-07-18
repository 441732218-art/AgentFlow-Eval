/* Shared Apache ECharts wrapper — Cyber Command defaults */

import { useEffect, useMemo, useRef } from "react";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import {
  LineChart,
  BarChart,
  RadarChart,
  HeatmapChart,
  GaugeChart,
  GraphChart,
  PieChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  RadarComponent,
  VisualMapComponent,
  TimelineComponent,
  TitleComponent,
  DatasetComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";
import { useThemeStore, isDarkTheme } from "@/stores/useThemeStore";

echarts.use([
  LineChart,
  BarChart,
  RadarChart,
  HeatmapChart,
  GaugeChart,
  GraphChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  RadarComponent,
  VisualMapComponent,
  TimelineComponent,
  TitleComponent,
  DatasetComponent,
  CanvasRenderer,
]);

const COLORS = {
  cyan: "#00D4FF",
  success: "#00FF9D",
  warning: "#FFC857",
  danger: "#FF3864",
  purple: "#8B5CF6",
  muted: "#5a7399",
};

const STATUS_PALETTE = [
  COLORS.cyan,
  COLORS.purple,
  COLORS.success,
  COLORS.danger,
  COLORS.warning,
  "#38bdf8",
  "#a78bfa",
  COLORS.muted,
];

export type SeriesPoint = { t: string; v: number };

type EChartProps = {
  option: EChartsOption;
  height?: number | string;
  loading?: boolean;
  className?: string;
  style?: React.CSSProperties;
  notMerge?: boolean;
};

export function EChart({
  option,
  height = 260,
  loading = false,
  className,
  style,
  notMerge = true,
}: EChartProps) {
  const mode = useThemeStore((s) => s.mode);
  const dark = isDarkTheme(mode);
  const ref = useRef<ReactEChartsCore>(null);

  const themed = useMemo(() => {
    const text = dark ? "#8ba3c7" : "#475569";
    const baseGrid =
      typeof option.grid === "object" && !Array.isArray(option.grid) ? option.grid : {};
    const baseTooltip =
      typeof option.tooltip === "object" && !Array.isArray(option.tooltip)
        ? option.tooltip
        : {};

    return {
      backgroundColor: "transparent",
      textStyle: { color: text, fontFamily: "Inter, sans-serif" },
      animationDuration: 600,
      animationEasing: "cubicOut",
      ...option,
      grid: {
        left: 48,
        right: 24,
        top: 40,
        bottom: 32,
        containLabel: false,
        ...baseGrid,
      },
      tooltip: {
        trigger: "axis",
        backgroundColor: dark ? "rgba(8,14,32,0.94)" : "rgba(255,255,255,0.96)",
        borderColor: dark ? "rgba(0,212,255,0.28)" : "rgba(2,132,199,0.2)",
        borderWidth: 1,
        textStyle: { color: dark ? "#e8f4ff" : "#0f172a", fontSize: 12 },
        extraCssText: "backdrop-filter: blur(8px); border-radius: 10px;",
        ...baseTooltip,
      },
    } as EChartsOption;
  }, [option, dark]);

  useEffect(() => {
    const inst = ref.current?.getEchartsInstance();
    if (inst) inst.resize();
  }, [height, themed]);

  useEffect(() => {
    const onResize = () => ref.current?.getEchartsInstance()?.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return (
    <ReactEChartsCore
      ref={ref}
      echarts={echarts}
      option={themed}
      showLoading={loading}
      notMerge={notMerge}
      lazyUpdate
      style={{ height, width: "100%", ...style }}
      className={className}
      opts={{ renderer: "canvas" }}
    />
  );
}

function axisStyle() {
  return {
    axisLine: { lineStyle: { color: "rgba(0,212,255,0.2)" } },
    axisLabel: { color: "#5a7399", fontSize: 10 },
    splitLine: { lineStyle: { color: "rgba(0,212,255,0.08)", type: "dashed" as const } },
  };
}

/** Multi-series smooth area line (single Y axis) */
export function buildLineOption(
  series: Array<{ name: string; data: SeriesPoint[]; color?: string }>,
  opts?: { yName?: string; area?: boolean }
): EChartsOption {
  const cats = series[0]?.data.map((d) => d.t) ?? [];
  const ax = axisStyle();
  return {
    color: series.map((s) => s.color || COLORS.cyan),
    legend: {
      data: series.map((s) => s.name),
      textStyle: { color: "#8ba3c7", fontSize: 11 },
      top: 0,
      icon: "roundRect",
      itemWidth: 12,
      itemHeight: 6,
    },
    xAxis: {
      type: "category",
      data: cats,
      boundaryGap: false,
      ...ax,
    },
    yAxis: {
      type: "value",
      name: opts?.yName,
      nameTextStyle: { color: "#5a7399", fontSize: 10 },
      ...ax,
    },
    series: series.map((s) => ({
      name: s.name,
      type: "line",
      smooth: true,
      showSymbol: false,
      emphasis: { focus: "series" },
      data: s.data.map((d) => d.v),
      areaStyle:
        opts?.area === false
          ? undefined
          : {
              color: {
                type: "linear",
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: (s.color || COLORS.cyan) + "44" },
                  { offset: 1, color: (s.color || COLORS.cyan) + "00" },
                ],
              },
            },
      lineStyle: { width: 2 },
    })),
  };
}

/** Dual Y-axis: left metric + right metric (e.g. tokens vs latency) */
export function buildDualAxisLineOption(
  left: { name: string; data: SeriesPoint[]; color?: string },
  right: { name: string; data: SeriesPoint[]; color?: string }
): EChartsOption {
  const cats = left.data.map((d) => d.t);
  const ax = axisStyle();
  const cL = left.color || COLORS.cyan;
  const cR = right.color || COLORS.warning;
  return {
    legend: {
      data: [left.name, right.name],
      textStyle: { color: "#8ba3c7", fontSize: 11 },
      top: 0,
    },
    xAxis: {
      type: "category",
      data: cats,
      boundaryGap: false,
      ...ax,
    },
    yAxis: [
      {
        type: "value",
        name: left.name,
        nameTextStyle: { color: cL, fontSize: 10 },
        ...ax,
        axisLabel: { ...ax.axisLabel, color: cL },
      },
      {
        type: "value",
        name: right.name,
        nameTextStyle: { color: cR, fontSize: 10 },
        splitLine: { show: false },
        axisLine: { lineStyle: { color: "rgba(255,200,87,0.25)" } },
        axisLabel: { color: cR, fontSize: 10 },
      },
    ],
    series: [
      {
        name: left.name,
        type: "line",
        smooth: true,
        showSymbol: false,
        yAxisIndex: 0,
        data: left.data.map((d) => d.v),
        lineStyle: { width: 2, color: cL },
        itemStyle: { color: cL },
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: cL + "40" },
              { offset: 1, color: cL + "00" },
            ],
          },
        },
      },
      {
        name: right.name,
        type: "line",
        smooth: true,
        showSymbol: false,
        yAxisIndex: 1,
        data: right.data.map((d) => d.v),
        lineStyle: { width: 2, color: cR },
        itemStyle: { color: cR },
      },
    ],
  };
}

export function buildBarOption(
  items: Array<{ name: string; value: number }>,
  opts?: { horizontal?: boolean; colors?: string[] }
): EChartsOption {
  const colors = opts?.colors || STATUS_PALETTE;
  const ax = axisStyle();
  if (opts?.horizontal) {
    return {
      grid: { left: 90, right: 24, top: 16, bottom: 24 },
      xAxis: { type: "value", ...ax },
      yAxis: {
        type: "category",
        data: items.map((i) => i.name),
        axisLabel: { color: "#8ba3c7", fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
      },
      series: [
        {
          type: "bar",
          data: items.map((i, idx) => ({
            value: i.value,
            itemStyle: {
              color: colors[idx % colors.length],
              borderRadius: [0, 6, 6, 0],
            },
          })),
          barMaxWidth: 18,
          label: {
            show: true,
            position: "right",
            color: "#8ba3c7",
            fontSize: 11,
          },
        },
      ],
    };
  }
  return {
    grid: { left: 40, right: 16, top: 24, bottom: 40 },
    xAxis: {
      type: "category",
      data: items.map((i) => i.name),
      axisLabel: { color: "#5a7399", fontSize: 10, rotate: items.length > 6 ? 30 : 0 },
      axisLine: { lineStyle: { color: "rgba(0,212,255,0.2)" } },
    },
    yAxis: { type: "value", ...ax },
    series: [
      {
        type: "bar",
        data: items.map((i, idx) => ({
          value: i.value,
          itemStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: colors[idx % colors.length] },
                { offset: 1, color: colors[idx % colors.length] + "55" },
              ],
            },
            borderRadius: [6, 6, 0, 0],
          },
        })),
        barMaxWidth: 36,
      },
    ],
  };
}

export function buildDonutOption(
  items: Array<{ name: string; value: number }>,
  opts?: { title?: string }
): EChartsOption {
  const total = items.reduce((s, i) => s + i.value, 0);
  return {
    color: STATUS_PALETTE,
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: {
      orient: "vertical",
      right: 4,
      top: "middle",
      textStyle: { color: "#8ba3c7", fontSize: 11 },
      itemWidth: 10,
      itemHeight: 10,
    },
    series: [
      {
        type: "pie",
        radius: ["48%", "72%"],
        center: ["38%", "50%"],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: "rgba(5,8,22,0.85)",
          borderWidth: 2,
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            formatter: "{b}\n{d}%",
            color: "#e8f4ff",
            fontSize: 12,
            fontWeight: 600,
          },
          scaleSize: 6,
        },
        data: items,
      },
    ],
    graphic: opts?.title
      ? [
          {
            type: "text",
            left: "28%",
            top: "44%",
            style: {
              text: String(total),
              fill: COLORS.cyan,
              fontSize: 20,
              fontWeight: 700,
              align: "center",
            },
          },
          {
            type: "text",
            left: "28%",
            top: "56%",
            style: {
              text: opts.title,
              fill: "#5a7399",
              fontSize: 11,
              align: "center",
            },
          },
        ]
      : undefined,
  };
}

export function buildRadarOption(
  indicators: Array<{ name: string; max: number }>,
  values: number[],
  name = "Agent"
): EChartsOption {
  return {
    color: [COLORS.cyan],
    radar: {
      indicator: indicators,
      splitLine: { lineStyle: { color: "rgba(0,212,255,0.12)" } },
      splitArea: {
        areaStyle: { color: ["rgba(0,212,255,0.02)", "rgba(139,92,246,0.04)"] },
      },
      axisName: { color: "#8ba3c7", fontSize: 11 },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            name,
            areaStyle: { color: "rgba(0,212,255,0.18)" },
            lineStyle: { color: COLORS.cyan, width: 2 },
            itemStyle: { color: COLORS.cyan },
          },
        ],
      },
    ],
  };
}

export function buildGaugeOption(value: number, name = "Health"): EChartsOption {
  const v = Math.round(value * 10) / 10;
  return {
    series: [
      {
        type: "gauge",
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        radius: "92%",
        center: ["50%", "55%"],
        progress: {
          show: true,
          width: 14,
          roundCap: true,
          itemStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: COLORS.danger },
                { offset: 0.5, color: COLORS.warning },
                { offset: 1, color: COLORS.success },
              ],
            },
          },
        },
        axisLine: {
          lineStyle: {
            width: 14,
            color: [[1, "rgba(0,212,255,0.08)"]],
          },
        },
        pointer: {
          show: true,
          length: "55%",
          width: 4,
          itemStyle: { color: COLORS.cyan },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        anchor: {
          show: true,
          size: 10,
          itemStyle: { color: COLORS.cyan, borderWidth: 2, borderColor: "#050816" },
        },
        detail: {
          valueAnimation: true,
          formatter: "{value}%",
          color: COLORS.cyan,
          fontSize: 26,
          fontWeight: 800,
          offsetCenter: [0, "28%"],
        },
        title: {
          offsetCenter: [0, "52%"],
          color: "#8ba3c7",
          fontSize: 12,
          fontWeight: 600,
        },
        data: [{ value: v, name }],
        animationDuration: 800,
      },
    ],
  };
}

export function buildHeatmapOption(
  xLabels: string[],
  yLabels: string[],
  data: Array<[number, number, number]>
): EChartsOption {
  return {
    tooltip: { position: "top" },
    grid: { left: 80, right: 24, top: 16, bottom: 40 },
    xAxis: {
      type: "category",
      data: xLabels,
      splitArea: { show: true },
      axisLabel: { color: "#5a7399", fontSize: 10 },
    },
    yAxis: {
      type: "category",
      data: yLabels,
      axisLabel: { color: "#5a7399", fontSize: 10 },
    },
    visualMap: {
      min: 0,
      max: Math.max(1, ...data.map((d) => d[2])),
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      inRange: { color: ["#0a1024", COLORS.purple, COLORS.cyan, COLORS.success] },
      textStyle: { color: "#8ba3c7" },
    },
    series: [
      {
        type: "heatmap",
        data,
        label: { show: false },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,212,255,0.5)" },
        },
      },
    ],
  };
}

export { COLORS as CHART_COLORS, STATUS_PALETTE };
