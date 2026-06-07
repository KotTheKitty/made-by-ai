from textwrap import dedent
from typing import Tuple
import math

def hex_to_rgb(hex6: str) -> Tuple[int,int,int]:
    h = hex6.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def rgb_to_hex(rgb: Tuple[int,int,int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def clamp255(x: float) -> int:
    return max(0, min(255, int(round(x))))

def solve_foreground_from_target(target: Tuple[int,int,int],
                                 bg: Tuple[int,int,int],
                                 alpha: float) -> Tuple[Tuple[float,float,float], bool]:
    """
    Returns:
      - computed foreground channels as floats (may be outside 0..255)
      - ok (True) if all channels are within [0,255], False if any is out of range
    Formula per channel: F = (T - (1-a)*B) / a
    """
    if alpha == 0:
        return (0.0,0.0,0.0), False
    inv_a = 1.0/alpha
    fg = []
    ok = True
    for tc, bc in zip(target, bg):
        fc = (tc - (1 - alpha)*bc) * inv_a
        fg.append(fc)
        if not (0.0 <= fc <= 255.0):
            ok = False
    return tuple(fg), ok

def composite_from_fg(fg: Tuple[float,float,float],
                      bg: Tuple[int,int,int],
                      alpha: float) -> Tuple[int,int,int]:
    comp = []
    for fc, bc in zip(fg, bg):
        c = alpha * fc + (1 - alpha) * bc
        comp.append(clamp255(c))
    return tuple(comp)

def find_minimal_adjusted_target(target: Tuple[int,int,int],
                                 bg: Tuple[int,int,int],
                                 alpha: float) -> Tuple[Tuple[int,int,int], Tuple[float,float,float]]:
    """
    Find the nearest (Euclidean in RGB) adjusted target T' such that solving for F from T' yields
    an F with all channels in [0,255]. Returns:
      - adjusted target T' (integers 0..255)
      - the corresponding valid foreground F (floats 0..255)
    Approach:
      - For each channel, the constraint for F in [0,255] gives a range for T':
          T' = a*F + (1-a)*B  where F in [0,255]
          -> T'_min = a*0 + (1-a)*B = (1-a)*B
             T'_max = a*255 + (1-a)*B = a*255 + (1-a)*B
      - So the valid interval for T' on each channel is [ (1-a)*B, a*255 + (1-a)*B ].
      - The nearest T' to the original target that lies inside the box defined by those intervals
        (component-wise clamp) is simply the per-channel clamped value of T to that interval.
      - Then compute F from that T'.
    This finds the closest T' in L-infinity? Actually it's the closest in L2 because the intervals
    are independent and the per-channel projection minimizes squared error.
    """
    t_adj = []
    for tc, bc in zip(target, bg):
        t_min = (1 - alpha) * bc
        t_max = alpha * 255 + (1 - alpha) * bc
        # clamp target channel into [t_min, t_max]
        tc_adj = tc
        if tc < t_min:
            tc_adj = t_min
        elif tc > t_max:
            tc_adj = t_max
        t_adj.append(int(round(tc_adj)))
    fg, ok = solve_foreground_from_target(tuple(t_adj), bg, alpha)
    # fg should now be within range
    fg_clamped = tuple(max(0.0, min(255.0, v)) for v in fg)
    return tuple(t_adj), fg_clamped

# High-level function combining behavior
def compute_with_suggestion(target_hex: str, bg_hex: str, alpha_hex: str):
    target = hex_to_rgb(target_hex)
    bg = hex_to_rgb(bg_hex)
    a_val = int(alpha_hex, 16) if all(c in "0123456789abcdefABCDEF" for c in alpha_hex) else float(alpha_hex)
    alpha = a_val / 255.0

    fg_raw, ok = solve_foreground_from_target(target, bg, alpha)
    if ok:
        fg_hex = rgb_to_hex(tuple(int(round(v)) for v in fg_raw))
        composite = composite_from_fg(fg_raw, bg, alpha)
        return {
            "foreground_hex": fg_hex,
            "foreground_float": tuple(fg_raw),
            "composite_hex": rgb_to_hex(composite),
            "composite_rgb": composite,
            "exact": True,
            "suggested_target_hex": None,
            "suggested_target_rgb": None
        }

    # otherwise compute minimally-adjusted target and corresponding (valid) foreground
    suggested_target_rgb, suggested_fg = find_minimal_adjusted_target(target, bg, alpha)
    suggested_target_hex = rgb_to_hex(suggested_target_rgb)
    suggested_fg_hex = rgb_to_hex(tuple(int(round(v)) for v in suggested_fg))
    composite = composite_from_fg(suggested_fg, bg, alpha)

    return {
        "foreground_hex": suggested_fg_hex,
        "foreground_float": tuple(suggested_fg),
        "composite_hex": rgb_to_hex(composite),
        "composite_rgb": composite,
        "exact": False,
        "suggested_target_hex": suggested_target_hex,
        "suggested_target_rgb": suggested_target_rgb
    }

if __name__ == "__main__":
    result = compute_with_suggestion("#ff00ff", "#ffbbc4", "66")
    print(result)

    print("color blending it so good ough")
    bg = input("hex color code of your background: ")
    target = input("hex color code for your damn target opaque color: ")
    alpha = input("fuckass transparency (the XX in #......XX): ")
    print("ok, calculating this bitch...")
    raw = compute_with_suggestion(target, bg, alpha)
    print(dedent(f"""
        found that damn thing!
        the result i{"s exact!" if raw.get("exact") else "sn't exact! fuck!"}
        the result is {raw.get("composite_hex")}
        {"the suggested opaque color is " + raw.get("suggested_target_hex") if not raw.get("exact") else ""}
        """))