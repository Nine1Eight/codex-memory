#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import zlib
from typing import Dict, Any


class SigilGlyphCapsule:
    VISIBLE = 'SIGILAGI_COLLAPSE_TO_TEXTUAL_GLYPH_IMAGE'
    BRAILLE = '⠎⠊⠛⠊⠇⠁⠛⠊⠉⠕⠇⠇⠁⠏⠎⠑'
    HANZI = '一二十'

    IDENTITY_SHA256 = '44209342fff30aa5af57ad97b6ceab96db7a0bc12a2fcc0d97e2e41c53e0deae'
    PAYLOAD_SHA256 = '27e6f36948f49fbc4b31b7ace3f167747b2dcaf2fc2db049070ab9c6d4cf9a03'

    MANIFEST = {
    "discount_combiner.py": {
        "sha256": "25216795dcbfe7d1e8be453b720c84229bf5ef82c2f1eecb43903723b8145fba",
        "size": 2435
    },
    "enhancement_discovery.py": {
        "sha256": "d11aafca3bb22884992dd76de234a38a82a6daa3aa800b5476f553d4da902dd2",
        "size": 1468
    },
    "proxy_pointer_rag.py": {
        "sha256": "192def42489109f9952b3c5e868b55c4cdd67a888beeda2e0c24e6b23080caa3",
        "size": 2525
    },
    "sigil_stack.py": {
        "sha256": "af7e7c98bca7235635cae5ca42a1ee12b7f582bd5237abbefc3654a5d9794f21",
        "size": 2410
    },
    "system_refiner.py": {
        "sha256": "72de62a7bde1381929d004d14c454fa5eb55429fe80c5249f9486a902012e43f",
        "size": 1310
    }
}

    ENCODED_PAYLOAD = 'c-plZYm?iy@vorj7c!w_`7-HDHIXNt+Ho^!(u|$She{d^L_!jJBuEqF`IM{vdv_NA2|gs9n@0AW_}B&Z{eqq*iPUjkt7;qP*-k1^&Wh7yG1-@S#<tsiUDc)7Zkf!AysQ{kDzA7YbEVgcU=m*OIOSRk?SPs`7Nj~AQXSme?<-OAT`D5>52>q&y^%5eeXUMwh5x>7umeE;O{nEBWi7(BqGteY$bDa@VzE{XK8j~z!E{xc+k2@J@AiSGHN4)ZIj_u<qLg_ltJ8u>Rk0;|IiH&s;xSHZEg!`8Q08?(i?IK&pK>Jt48IJV1_JMqg$3K?c?$24L_>a;%D-8eT1wXw`bXDq1jr$i3S=N-=Cr_sIsn29mqMryb%8<?2`hnN;!WGdrmPTUEL62HJOUZ^0Y3;}jjiSp^0sl{d-*6pGOPio2Q043QmFXE5|Pv~s<un4xl6<z%mK))w%b69bRQ8#deP`}<*R1Xm0QTBujs<kPEv$LW_As<gdYBqX<|G`;axy*EHBw=6GrS_oR%rib_r+Yf(2l*R;57H49y`7eY$y)Y;ggP?nTFtu9G+8MIlr|G=!r7NNMnyL|J#UH0gR*fn%lCP>CRPj1`z5ImgB$P3{|b_6?hRZ}3xcsRjELb^Nw0^D<aZ8tAOn7264>ay3=r0FL}1){}-V`~b75L_4uM@o7M<tTrudSu2H}y);w@ZXZudwHAqSCs4B%v=}K@R6%FoJt&uK94yx}jV^D%IX<5CJQc!HGX4S<^C{@AhMzcBl~l%i{pULY1fls_9>?iGe`L!g_=<JC^<-p^M5GnRrNG|MjEvB}U}RA<<Bc!SRcCWB?z?cfLM!NuKL!97^%k3&O%S_>F47^f<oH)fg}@ZJ9UP6gc;raAO5{b_`lM+wLc_p-_v=Zm^e_@G*i*yUxo5^!ONO6U11Iq;-MRM=06$OTk4=C?uLdz1@#0N%4I0U8pz-D^G>N<cHww50Zw!_YNc!fUbaoBRC7u?sQPx#FzK5{iB3WHuK|2p0kJ!)!2Vab@>ACg{f_yNBI=%^1F=nGSmyd6;D+Ryz4XYGT5vjgiv@y1oiF-046m&tw(`^sqvJ}@70^JVP)x`EGyM}I!9r5g?2Lig8L=&NoT*V@TFlP375asDJtHExm*OYdq*7GZ*x9w(c++HJ9(y#EC>5Qi-xUyd`9YtN5t5QHJg>@1rT`yHGjvbe6Pr4G>7Ia@xCE({cO1)#bZ{gcOtgj}>7BtCY4G*Ex4E$YZ2grZmeR;gK`i$7z58bBVxs2$lc7(gIL<|x>TwBBd^sqZ+22uYF`>J1J0RJv*js!@^hPL!Ub9*_D#y~1rr4+8#lkZgwUIsBg&dZ|K<a0@N1d_%O5fo}v!hHYw9s5}G6t-egvsB)T^aNj-#6+<J(<yif3j-fDni?Z3fckhgSo|DzIJfd&4$G_0;r;F=@2``jE&gfKXRz(s3U=fgLKy=OP<aNvP~@qEN?xj>uJlbFoq@b!U;iE^zq-lfhl=lHDt{BOFa$pGdRFi%K0b@xzstiB3$?vG0L>VEA$iIe3|TV`Yh;`yrQC!3q`tq&HHCh3;NNA_H+lXkhbWkdL;{)23$3ux$6A&cif`+gTC<9g(=rW_R_`S+T^$8hXcFRLFDw>izL)6*^X>+)@vdd%GrECtZ`E+M>BJ|K25})u9<cG_X<OtFYDBpO7yF~f2)*G!)byciWg#*SF~r@Jwm;wg^3NaM{<MAn7RyvIgVa%gyaFg?R<Ec3;?v*e)4y&vU)pMNt*Gy<@_V7ce1l3nRx}o9vjp}t)|9MFR@E%cKS8nysi~>332C;Sf&C|t&S<G{)1P@X0|Xne?8=xYq(9YY2r;*rs5q|CPiB6`{TVg%vr!Pl&6^{M6uhqbB=9e5;inXD9sv;Q7bdcuND|PBc5lH{K?iKd57T@<{gju9X1{y~-mAgyp|n@`O*1vM0@I9)hgsv%n67eG<wX;=^)n|Dn6CVRghhYuFv6glwBDdD84VyP6Po!$f3)DJY>9BXidsEI7j^U*#JTw7s0++qOY>!RTjHN~w<QG1DsXqm!P7Zx^Zd6MT4W6Gk9p$Bwb}<{^iCdV<-MT<wfufnl-Jc_@E+KDIuGKnUArHF$$em%?o<GP(S=5F0C)v2a2vR!x(05clz~>7eaT+V<}JKx<`k(=mOVeD;a;>8DIAsyM>d14UM$(LA0Vo)%hdQlz=uML*lzfc#7&orf&563c(EIo;oRpNLcF#U7aoGO;l(cWOH`bK>N*QJ3DAk}3%2XrH}b&+J$yw20|>S={jtO$P!>D@@&h3}AObi2s}4e6-fDLXZ#RmEGT>C2&E_PBoxOR6EbKF6`2`DLnJ)mn<I!61GCo>g{#avMVqG~ew)bvk{MB>XgpVe1pzzxiLQ94npgm~^d>q}*A^DR=sEcn*<hoW2@t_%_QBdm&CK;m(;AWJQ2CyCSk|B8wi4B~!bYv}}6~e(_#vpvN9G%Qu8p>%UApoNM9kr{)-Q9dMD@Bp=SU^v+1{`Q*))V+2LU&)vA{e9f%Gl?^$j5YRl3Hlo-Ui)Ez_g3krpGjm`Ac{i!7zs?_VOaA3+Ij$cYhI~Q=K8!em!|=nK=J>zIeis9|p$85F!S$4bP)>YHym;DK4#i`{m^$l$X=TRU;XQdU)rAI#ykpl~xOKy$#iwS{`J&rK!#TYc$aoj;<E%ABnX{-D91obBbWG2bHkH?iFAb-1g<BF=}@DKu_PBhZb^lKI0I^<|%&l_W|Yh`rY>*P;w)+-;bm1L|$TxR+S`3mhux&SRHwVOg`8~B<6)C?#XjG_5{aMQc~OVDB{`_gjt?oa~nB&0W*teZeNHJVphhWR=l4*tI)exBQ^S34pbEkPHs3(s(U&aLRqyeyBZn5wfb0&sv_v*7)a_+Hi|4a<Cy0$HEWKse4`6+?7Uo0QeLb0_;QZH4`<6u??@stCw|M9ba3F>JGc$Q|7ouWS$ys7V^0&@E?;*xxf^bR&0(i*?$0U@>8UtQO_Uf6GT-6LAF;sFjB>~xmcgzO476*!`jqW(9%9W9EEo+gK4MG(BRxpW4rr2edL+Q4lRB1YtYGj;qfw5`P@YiMClf{26GP<LgZXT3DWXjQY=qgL{l*BpFh;D}CJUk@FaT0#Xk$1O5qO~6bWN5q*JFto&sB^BuoJ`44^|7}u>f{KJhzx__WPY2Tc;Y~*EpF!CCWsJblT|;olV#Vkz=sQm5hOZ$_G$OD!GSn#XcROr$>&pC?7EBb35w-&pX^!sjA9+$fGw+2G4DM_Tn)u38U}oolFT{5}OmVuJ^gK;g@&dOmjak^27EhEA22))V5%SOxm&j);O%jjR?_CDV;9wI{6j_o;1rE1=;UlAT0>ycFLuNaeXU6jZdGPTP)~z5s^84pjY4VREzUDy0Ri!V=}s`TLo7=<J(=HSN0t^fZW>y4tjsVLYvb9QyVyr+w+d*sGv`y8ZQW&;~1=+8l_;>9gfcTMkn_kc4GuI3?5&jJGfss^{x7EHvJ*sh(TXF)3Wx7TiDBi$2yB7GVFCU?(m66>Ig_jF9x*pXmDQDt(^X-gQ`y6zd1CsajFeq&DbmvqL@-NV>prlQaENG_Zm_TM6fnWT`GjEOPcm{$MxX+Dl&uh(POQPp^E5ABJaq^G;;Jjz-{cZ^mSa)6zrDuxPY^8%MSp|ZU|v7FMxF2#KMMMgYaraL$xm=(yWz>yFT_uTUA}8V$~Qyzti^RWl4BuOAhU>goYRr0F;GRnrH(dC1~%J6*0XV&YrOC#bF*U&}(UFG$S03Ta5b9|I^J(g8Awo9BH!^ba`8p1pagkzrJM11~zTsX7tz`-r&MG=^Jk~X+$Q_3U$5fnNj<$p)zV|2*($+lAhtn*_?Kd0ABbZiBFJW(d>GCr{)Z3k{2c=K`~>p5z=WMK@l<gH<V>TOMm45XrtNd99|l7Hs01V6;v<#lO?yu)nyv(1mq%}4T<gVM2sPNKjoku&qL3)X4#NCIsX^c9`S$'

    @classmethod
    def identity_hash(cls) -> str:
        raw = f"{cls.VISIBLE}{cls.BRAILLE}{cls.HANZI}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def decode_payload(cls) -> Dict[str, str]:
        compressed = base64.b85decode(cls.ENCODED_PAYLOAD.encode("ascii"))
        raw = zlib.decompress(compressed)
        actual = hashlib.sha256(raw).hexdigest()
        if actual != cls.PAYLOAD_SHA256:
            raise RuntimeError(f"payload hash mismatch: {actual} != {cls.PAYLOAD_SHA256}")
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise TypeError("decoded payload must be a mapping of filename -> source")
        return data

    @classmethod
    def textual_glyph_image(cls) -> str:
        return f'''
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SIGILAGI REHYDRATING GLYPH CAPSULE                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  α-layer: {cls.VISIBLE:<64}║
║  β-layer: {cls.BRAILLE:<64}║
║  γ-layer: {cls.HANZI:<64}║
║  Identity SHA256: {cls.IDENTITY_SHA256[:64]}║
║  Payload  SHA256: {cls.PAYLOAD_SHA256[:64]}║
║                                                                              ║
║  MODE: Embedded source archive → verify → write → import → execute          ║
║  FILES: {len(cls.MANIFEST):<3} modules                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
'''.strip("\n")

    @classmethod
    def verify(cls) -> Dict[str, Any]:
        payload = cls.decode_payload()
        identity_ok = cls.identity_hash() == cls.IDENTITY_SHA256
        payload_ok = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest() == cls.PAYLOAD_SHA256

        files = {}
        for name, src in payload.items():
            digest = hashlib.sha256(src.encode("utf-8")).hexdigest()
            expected = cls.MANIFEST[name]["sha256"]
            files[name] = {
                "ok": digest == expected,
                "sha256": digest,
                "expected": expected,
                "size": len(src.encode("utf-8")),
            }

        all_files_ok = all(v["ok"] for v in files.values())
        return {
            "identity_ok": identity_ok,
            "payload_ok": payload_ok,
            "all_files_ok": all_files_ok,
            "file_count": len(files),
            "files": files,
        }

    @classmethod
    def rehydrate(cls, output_dir: str | os.PathLike[str]) -> Dict[str, Any]:
        out = Path(output_dir).expanduser().resolve()
        out.mkdir(parents=True, exist_ok=True)

        payload = cls.decode_payload()
        written = []

        for name, src in payload.items():
            file_path = out / name
            file_path.write_text(src, encoding="utf-8")
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            expected = cls.MANIFEST[name]["sha256"]
            if actual != expected:
                raise RuntimeError(f"file hash mismatch for {name}: {actual} != {expected}")
            written.append({
                "file": str(file_path),
                "sha256": actual,
                "size": file_path.stat().st_size,
            })

        return {
            "output_dir": str(out),
            "written": written,
            "count": len(written),
        }

    @classmethod
    def boot(cls, output_dir: str | os.PathLike[str]) -> Dict[str, Any]:
        out = Path(output_dir).expanduser().resolve()
        stack_path = out / "sigil_stack.py"
        if not stack_path.exists():
            raise FileNotFoundError(f"missing rehydrated file: {stack_path}")

        if str(out) not in sys.path:
            sys.path.insert(0, str(out))

        spec = importlib.util.spec_from_file_location("sigil_stack", stack_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load sigil_stack.py")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        stack = mod.SigilAGIStack()
        result = stack.demo()

        return {
            "boot_module": str(stack_path),
            "demo_result": result,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="SigilAGI self-rehydrating glyph capsule")
    parser.add_argument("--out", default="./sigilagi_capsule_out", help="rehydration directory")
    parser.add_argument("--verify-only", action="store_true", help="verify capsule without writing files")
    parser.add_argument("--no-boot", action="store_true", help="rehydrate files but do not import/execute stack")
    args = parser.parse_args()

    print(SigilGlyphCapsule.textual_glyph_image())

    report = SigilGlyphCapsule.verify()
    print(json.dumps({
        "verify": {
            "identity_ok": report["identity_ok"],
            "payload_ok": report["payload_ok"],
            "all_files_ok": report["all_files_ok"],
            "file_count": report["file_count"],
        }
    }, indent=2))

    if not (report["identity_ok"] and report["payload_ok"] and report["all_files_ok"]):
        raise SystemExit(2)

    if args.verify_only:
        return 0

    rehydrated = SigilGlyphCapsule.rehydrate(args.out)
    print(json.dumps({"rehydrate": rehydrated}, indent=2))

    if args.no_boot:
        return 0

    booted = SigilGlyphCapsule.boot(args.out)
    print(json.dumps({"boot": booted}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

