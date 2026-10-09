"""
compute_cp.py

Reads a CSV logged by serial_logger.py (columns: time_ms, P_ch0..P_ch5)
and computes the pressure coefficient Cp at each tap.

Assumes:
  - CH0-CH4 (or however many taps you have wired) are surface pressure taps,
    each measuring (P_tap - P_static_reference).
  - CH5 is the pitot channel, measuring (P_total - P_static_reference) = dynamic
    pressure q_inf, since it shares the same static reference line as the taps.
  - Cp = P_tap_measured / q_inf   (since both sensors reference the same static line,
    the P_static term cancels out algebraically).

Adjust TAP_CHANNELS / PITOT_CHANNEL / tap x/c labels below to match your actual
wiring order before running.

Usage:
    python compute_cp.py aerofoil_run_20260803_143000.csv
    python compute_cp.py aerofoil_run_20260803_143000.csv --start 5 --end 25
"""

import argparse
import sys

import pandas as pd
import matplotlib.pyplot as plt

# --- Configure this to match your actual tap layout ---
# Updated layout: CH0=U1, CH1=U2, CH2=U3, CH3=L1, CH4=REF (pitot). CH5 unused (faulty sensor).
PITOT_CHANNEL = "P_ch4"
TAP_CHANNELS = {
    "P_ch0": {"label": "U1", "surface": "upper", "x_c": 0.025},
    "P_ch1": {"label": "U2", "surface": "upper", "x_c": 0.150},
    "P_ch2": {"label": "U3", "surface": "upper", "x_c": 0.350},
    "P_ch3": {"label": "L1", "surface": "lower", "x_c": 0.150},
}


def main():
    parser = argparse.ArgumentParser(description="Compute Cp distribution from logged sensor data.")
    parser.add_argument("csv_file", help="Path to CSV file from serial_logger.py")
    parser.add_argument("--start", type=float, default=None,
                         help="Start of steady-state averaging window, in seconds from log start")
    parser.add_argument("--end", type=float, default=None,
                         help="End of steady-state averaging window, in seconds from log start")
    parser.add_argument("--out", default="cp_results.csv", help="Output CSV filename for Cp results")
    parser.add_argument("--no-plot", action="store_true", help="Skip generating the Cp plot")
    args = parser.parse_args()

    df = pd.read_csv(args.csv_file)
    df["time_s"] = (df["time_ms"] - df["time_ms"].iloc[0]) / 1000.0

    # Trim to steady-state window if given
    if args.start is not None:
        df = df[df["time_s"] >= args.start]
    if args.end is not None:
        df = df[df["time_s"] <= args.end]

    if df.empty:
        print("No data left after applying --start/--end window. Check your time range.")
        sys.exit(1)

    print(f"Averaging over {len(df)} rows "
          f"({df['time_s'].min():.1f}s to {df['time_s'].max():.1f}s)\n")

    q_inf = df[PITOT_CHANNEL].mean()
    q_std = df[PITOT_CHANNEL].std()
    print(f"Freestream dynamic pressure q_inf = {q_inf:.3f} Pa (std dev {q_std:.3f} Pa)")

    if q_inf <= 0:
        print("WARNING: q_inf is zero or negative - check pitot wiring/orientation, "
              "or that airflow is actually running.")

    results = []
    for ch, meta in TAP_CHANNELS.items():
        if ch not in df.columns:
            print(f"WARNING: {ch} not found in CSV columns, skipping.")
            continue

        p_mean = df[ch].mean()
        p_std = df[ch].std()
        cp = p_mean / q_inf if q_inf else float("nan")

        results.append({
            "channel": ch,
            "label": meta["label"],
            "surface": meta["surface"],
            "x_c": meta["x_c"],
            "P_mean_Pa": round(p_mean, 3),
            "P_std_Pa": round(p_std, 3),
            "Cp": round(cp, 4),
        })

    results_df = pd.DataFrame(results).sort_values(["surface", "x_c"])
    print("\n--- Cp Results ---")
    print(results_df.to_string(index=False))

    results_df.to_csv(args.out, index=False)
    print(f"\nSaved results to {args.out}")

    if not args.no_plot:
        fig, ax = plt.subplots(figsize=(7, 5))
        for surface, marker in [("upper", "o-"), ("lower", "s-")]:
            sub = results_df[results_df["surface"] == surface]
            if not sub.empty:
                ax.plot(sub["x_c"], sub["Cp"], marker, label=f"{surface} surface")

        ax.invert_yaxis()  # aerodynamic convention: Cp axis flipped
        ax.set_xlabel("x/c")
        ax.set_ylabel("Cp")
        ax.set_title("NACA 2412 Pressure Distribution")
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        plot_file = args.out.replace(".csv", "_plot.png")
        fig.savefig(plot_file, dpi=150)
        print(f"Saved plot to {plot_file}")


if __name__ == "__main__":
    main()
