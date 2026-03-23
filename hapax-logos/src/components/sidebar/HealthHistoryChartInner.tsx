import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { useTheme } from "../../theme/ThemeProvider";

interface HealthEntry {
  timestamp: string;
  healthy: number;
  degraded: number;
  failed: number;
}

interface Props {
  entries: HealthEntry[];
}

export default function HealthHistoryChartInner({ entries }: Props) {
  const { palette } = useTheme();
  const chartData = entries.map((e) => ({
    time: new Date(e.timestamp).toLocaleDateString("en", { weekday: "short", hour: "numeric" }),
    healthy: e.healthy,
    degraded: e.degraded,
    failed: e.failed,
  }));

  return (
    <div className="h-24 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 2, right: 4, left: 0, bottom: 0 }}>
          <XAxis dataKey="time" tick={{ fontSize: 8, fill: palette["zinc-500"] }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 8, fill: palette["zinc-500"] }} width={25} />
          <Tooltip
            contentStyle={{ backgroundColor: palette["zinc-800"], border: `1px solid ${palette["zinc-700"]}`, fontSize: 10, color: palette["zinc-200"] }}
            labelStyle={{ color: palette["zinc-400"] }}
          />
          <Area type="monotone" dataKey="healthy" stackId="1" stroke={palette["green-400"]} fill={palette["green-400"]} fillOpacity={0.3} />
          <Area type="monotone" dataKey="degraded" stackId="1" stroke={palette["yellow-400"]} fill={palette["yellow-400"]} fillOpacity={0.3} />
          <Area type="monotone" dataKey="failed" stackId="1" stroke={palette["red-400"]} fill={palette["red-400"]} fillOpacity={0.3} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
