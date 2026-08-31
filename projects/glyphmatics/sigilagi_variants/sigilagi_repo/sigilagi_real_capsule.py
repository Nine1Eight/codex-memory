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
    PAYLOAD_SHA256 = 'a59e7610403c5d32729bfe760c6d8e1132a341cd8d18f1e7947d56b9be1d17fc'
    ENTRY_MODULE = 'sigil_stack.py'
    ENTRY_CLASS = 'SigilAGIStack'
    ENTRY_METHOD = 'demo'
    METADATA = {
    "name": "sigilagi-real",
    "slice": "query-interface-indexed-capsule",
    "version": "v8"
}
    MANIFEST = {
    "build_index.py": {
        "sha256": "178e4081f576b2ebed76f4b58bd81f643c87f74ddbb35b258dcf4de7a7b6ee8c",
        "size": 2219
    },
    "corpus.json": {
        "sha256": "656980e88297b4dc91b07352daea00435f55ed2e64e5c1a3bf57294fb136a330",
        "size": 604
    },
    "discount_combiner.py": {
        "sha256": "c8acbd07442bc95e74f596b08a61a73a0ca95fbbb58d6f5b5d7b69cffff24fb3",
        "size": 1409
    },
    "enhancement_discovery.py": {
        "sha256": "23eaf9ffa500d13027607278358ddc0be5546379074cb749e26b9de032a2ada9",
        "size": 1349
    },
    "index.json": {
        "sha256": "115994d52464043cce214a3956f4743c92b85b0b3a338e297cccd9754b854311",
        "size": 2387
    },
    "indexed_loader.py": {
        "sha256": "ebf70ef6e31568ff49bf88ea1b0f5b6b073d5a0c6d8d2aa0176010bbde0e40fc",
        "size": 806
    },
    "query_cli.py": {
        "sha256": "ce5e7dbc3c7b0044403c5a5004f9d9c3d67c259f62229fec33cdef0759954dc9",
        "size": 573
    },
    "query_engine.py": {
        "sha256": "be596a022d114010f52e0d4ccaffe4cab1514d23e61ce55243210dfe055292d0",
        "size": 748
    },
    "registry_manifest.py": {
        "sha256": "dc5886fc2360659e367e9a0a2712eee9e0e2c7c488b8418e0f78dd87597ebe3c",
        "size": 1256
    },
    "retrieval_index.py": {
        "sha256": "bf724666d3f645985857697de4b463e48bb9a2beb5721095cab053e86b72d991",
        "size": 1266
    },
    "sigil_stack.py": {
        "sha256": "5ad35efde16c822e12a1862ee03e618f856946cb59ab823332a6e55a8b5671bf",
        "size": 3158
    },
    "system_refiner.py": {
        "sha256": "276f899f3361837e8e1a887ec3d08ac2b608405df19b4abd9c2d78f916c24f35",
        "size": 1024
    }
}

    ENCODED_PAYLOAD = (
        'c-qArU6b3!?XPT<hma|czO(C0Myb+x5<BCL<D_<`FOr7C6IXYPDUu;6`_!xcdjae>xztgq-RR|{B^JN}SS)}A?|yc@&x<U{%Z%T}^<g%jeg4^_ecL>`&dW!<e9!7bcUzTDR^_&-b}UJ@`)=RxBw_iku9}XeWm$D;mse%GDp#c({jIG^Ii*g!+akYK@V~%M`J_A4d3mEA{E%<Dh&?M05qp)l9U@x+S6kLq?|7O2n+F}g>*lQOnvh+5OF&Ebv7WC=2A_rlV<lSxcnrgN9js<?H2>zazX#!ReSci7R<kcwvoJ2I54;INwyhe(&GM2V=D4kkyo2$aNJ<>x+Av~?D#)r$I~P14<H!gxzg`n_?wI5-FW>W~<JsJLtXHvS3kFOQARtfLu4=dq*&`#t#ROamOv0tK6_OzSBKD3S7Dc+d&Qb<cv*l`rsPk+!TZfV<MK8|)BcR8b4x9l)DLFtm;DYRUmu6{~0$2w8B3yjKJ5YssvYJJ}co@3WX|+p1l$K^5<42L26Aw}Up}{@Z99TeFO!#RzFO!ZpyB3!MtXZ6pMZhC63ES#yVUZ@c8qVPB!Qf|8m0e!$x%<RSiPJ0#@LSl!FD)eo2Ep>uebEtE#FpzYPV1VNq+*a(Xxo5dN?V#itA>^cgCdrO;*M)<ayMCe5H_)?_9ZEz;ANmS7e+Q5VsZf$5f=_^6d^Pk=c$?_HXOpK5earQJ9C%jWk4G*FFU#D>$K&tO!PMaxUIYZrxnHxZ>!=x55l-k8x9<nLQhS-ZxeJ?FokA50v5z@OwMd3Agg^h029trLCL+oW#AWW#4*2vz1{}4Ej4KlI9>p6udD6_NGyBaG*uI9!KU-JMeisuFyw#E?k#*r@MVgc+;YeQxVJQG1DkNe(=0(V4tTk#GQhf6&Gy~);%h(=I{fB9v+dGy!voqxtN@;e9RGT#x!_a@iS71n$F4a`*+1U?{F>(341%hG!R6Z6Y96t?<7BS9-0ygkc7mu)ZpaqSiO9M1H)Wr-t>%sB+~-HYL+H|yRoB1qjo{FtW&EBXTZ*Z`t@1$jxR?IF(qcc(fYPe;xU^;OTsBZtYKsrtpkj}XL6U{ztD`ZuX+bNeebS4P^Tr7y-rM%BTFGsh*6nSDXGH&~)G%uQ#2*?!FRaqwA_LC$ySfb&GO!ZBQg(~S5xJ}c&a`&%YqNKp&d{*sLn+w00ml$1;-TZ?E`=Wf^(RT0?l87lEI=Mff^H>AKpqmF6#Vwkf?S^8L98I$4q%%_wy%I7YKb$X_H3=KW;ey5zP$iwu6Z<STFrjM$3H<l1^WeoV5@BQEpJ&>vW%l=%}dx?`G&QJ-E~#K7k<Y#dknz9t~a+ZCxeyU<QTueytKrhbyH>gO@3W))-`F_!UlxX$Kt?N{{3oJqzB#zjs&X|nH;0hWl4$$@1owwhv26{%pANRtYw>*ob7-u;0Zl@2`9jTfroE#DLLvq?+(O2Z2gXF^J+!7;|Sxr0<(Lc7I{XY=(Lp?o*!CWo8RQcMU&omm-kCk-5pq6fr;^ky?OQ{BaH#qC~vSbPz3PCDp(v@^Bt%N(1X(}JEb8s#TM+8Z_vnuCc)y$8!pz%?`qK78EcbN)#6s=n(Q>oTRNKIfZjoj&l?f-Pl@gc2FY!Tw8a%lAU))b>oLNOOmr_c+jn|SP&FBE#D-p#Gz7qc$2VXbbG?Bp@E8Y-0_35MdzCz!`1uYbYyEtWet6Eda2(29!o~f)T)xDQQA7d`EANsdXnC=vXySEM^0^&57TdT1rcCH>7+uTr&ESLJE<tF*7cu-gch+{AhB^fBN9YAWe;9-|NvTvxvE5&HpuR$iVLUUz4^S&|o>`|fMMnDu!z36b6oEn++A%fSXCwBpEhG1Ux#nB+XA6aL5K-f#7_}(eZ_S$xrx0=&S1Th1Yz;<Dfkgf#BWcB?e2C4iE-&NDFk+8;@ii}o^tL%{%ZI3e!wCdMLkH1Ea(M$fE%zYwMGE_}-Pbk6<c6TI>3hwo9rFz}<cQ)zV;L@As(K{K5UvGx7rGLnjXxqE6f&iu@P`+Q#H7K5(0p)$bp#aOyg+JMB21A>^Z};ZPIyBpp&roDk>oJn5lEE16Za%vH9~6dgTtYg7KxtWrwnHY0wnfIT-=~NHPuH&>JR71uWq&rZl0I77%t-pBj~`{b2!u0PpHobpZeSo`$5sN{Hmg_yb_+~^PVFzC7oWK!`eO|T#WHX>MoA^l`e%y$q;sPi-)PoOCxp}vTqmcNpE{98YlOLI*d>O;9|Vi2f<6h#aaBi0vYajmSYrSDF%%0_kG@=BE2XeZ=;+NaeOa#xeSFsPwf`NyY7~wQ_6Q>G;T-)As;4<@c{YJ@&+CUb+!b)dQbo_%MGrD_c$b@NN@Or<^O!$^5#9bMq7*EC5q|;>(T}^{Edi^FsItwLWtRrDSKl=zX#}<i&g9(TlpJ%{J#q7>4SoLE|y?IMv+xa5YQ_SgbFE{kPaBuegh_Auw^-g*WKY<S*Vy1{rAU~%3r6O4@}#jN1|Bc4C{H7?{Yj>?fI>g55(<|L><t28V<=hBqH$VApz-CQV3?1S?}g7xVT%|OI$|`2jqg*cIi`|Itm+kZc|MHUro~MRo<RNdaxCNzsv^g)N*c)vVNLi)z}7Uo_ctU%<MlcIhAETo$Z)>?d;W=si#-?XJo4VWm?JRA6TbO`%W+P|DLnznyuo<SK-yBEO6n_(r|AHMhvba7hZ%!)(m?`45yrewuCk)Z9KpWYPg5FZ+-???beA*3uBy&-7&p$S35wav_D-fdiS5PL~S(F$w)VJ29fQ+xX#rwVc(H2JcF)s7Lzq7x88JFXa_Z!gm!h)XOJ(P41SjS(cw&At#n{#Oc2iMoC)A4r-MtkJrx*T<r(n$<UB*5_Nh5ZUG{-|79D-`OkWS3Ak!!4gLU#^#DR7O1w6o~W0zsh8DcUK&KZ+D-tEL1Oms1MAu^bG2;M%u-CN!#U$4reieBMJ$6Ls=Ys+W1iuC$TOhw|QVB-~WF;?OgS4($vB}A2D_8+1-T9!57>SEc9gt5p!K~+s)-80+OSrm#XE{|4X<)vqjr0@QC;vF&}QCG-4wEdFe@G7~_$CT^jQ&-AU?r!D5*S}S^Zf)%(N>ov(ZN$ynT`P@r(iC~3&!g4FBIUL)xG$(z1Q!tF1!T}$sGKq3Mp&*(Qb1g&6VZzyN5kV_g_I^z@Q*3t?|a@Hl1-6+#Ez}BxvA3zPR9P0A}r)>5>VsjokH^#ho1fT@+}UYZp9$P4Tw__iJvt$6ifa>PlAlMn<lT3C$J@jnbA7g_pe^+3vz)8+h&qfq5xYVIMnJbFKR&WPnw4(WqI?!)QgL*sxRK*WbiS3kz>hKw%jb9XpFD-yK7iMwPm+Cq(5CHb)vBYN^EeDMCcEaX#=aHrUje;;|LC2#lB2v1p!Wo=__zk)ycaBjnG%;BHOwr7ii5bdH5+Vw}rv+@&=NRk5fd}mZif6u@4pC8#PRxT*Hd<C{ZD+fff&blH>MKK*sQ#SRX$KG#B$8<wz5q52%b^-|6&uVK5J1WTj!DDcDB^7=>hwWKYMFGzz)`g=tSv>6>Do@x<^5$tO~!>(rBn4B7Fb$8X&7wAtJSjt$!8CtEoB)q7vZp4^mku>j8%2w<g-KKwFxjO^i4{Ofz@_Lm`4=-z=?&Uqju7ay!=X~#NiBNj0ftFSW|mhNCO?T~?KeyY2cz7d{%f2}#3qQsW`fhZX%zcnb0I^iSyc<O;@Axh?^(s+TLkxc~wtTMd|S)9Glw^bLOl-wzKwY^H1UHr9j5!?&j60zjrB#h+hB#h?xB$S<pd4P_?ek{teMclt03RER3UIAbYDgl=At-L3EkrwS3U$=)0o9{;9j=o-6a#FM;-XxM$>9ORmxoK{G*cg}AdadqMIp##sc;$IWX#JAlmtVg7fG6b~?RXL`DZO>PuQS9W<~wBcrhhnKAH6)*yJyINe6&8bmj<)+v-S7}8<G-F)+aU*wfhYws^`95L1UZP=^30*W;kxTezHn8;owrc7b|=^7i&iV<3WS65bs^K&jPImN%ge{A^T+2)1^vS)`Lt`Brh&(Kc&&v;oqT5^UaP!W{{cnOnkHAQ@>rIcbo`59twM=v<jF8e-M^lCgHSOsqiRjZS_%;llyMP;Kcw>ufKf%0$X}j3zTl*$17CbyYFcR5=>a{K8OLDCk7*iT}<pR>?*#rxuQVqL@R_&>3Ip}zkt;2F2HDsRuD$)s`u)HqSmAz5@LcDBe=m{;9>0n-#J+r%T<dQ#8)RTgH5BQWWWd1s*4iYeWh7^B$gMkuR{OCG6&k7L~r_^m-DNutF?EE(+Ev-%*c8qN~rD*iB*h-ME_o_=J@&L{2trJ<O>taFOY#R)+qn0D@^rIUNocdM(>!VP~-)(X#@9$smnQSBhdwF<?|mapPTsRmntaG`3E66-e)zsra+@_#Gq<8?Ki9%+HNOj<n&g`+1@@Vg~8XibbhKy@NV5x0Xt>LKalX+dA9<z@>%=Pa;ggFH?>MVEL;@?{k~JJgT+An16U*Og;&yp306wnm+}A>U%ml_HdEj5@#f|ziQZ#J;tIm8;3gU0RaX4z6RIeeTIaoE34yzW{yRh=6<$5!F`T>B61e0-_kA}@ZLw}iwzo>4dQ}!zml3s9FEIGqmz&$GORS7xW9P!^$c;pIHGspp6#hY4j}5K&dHvL)BRg>wm8XKph_S?jBxLCi!<DZAf9FXkeQog`u(7sE52&vq-~k(4n0Qh3<6aL?uSVy~!5ydX0dU@T^K&|UxE|Zav7M;(dcp1Vbm7T{O;YN6DrM$-RAYwJ>KNDuA_RrE7>EAjp_%pkf#rMycT-00;=^7sPgZy*#kQk)CQ<0SAosA>9%8^f)|o{Fycm}EhNVRHMuv?Y_fKZ3V`4jrzdZ%tQwAstJ}np9*)7}X))&%&=xT0t3F6qVhd3C;Rht*9!h%?jk=2fKPwBHRh|u$+t9xxkvQKc)^JwbrimS)ylWfVr6YvS*(pBdj#zE)~=>D2U!eOVl*)P!!a>MXspS;twX<^i>qHah(4!37|u1sLrf6|YNk0V=ZtWe_A>&%uKf)RO(lL3fTuajRrSR8E$Y|fD1^^F$W9F3jS)|k9}?@f;*vf<WKYjx-`rkAqhTRh5b^*YHcM<bj5HdVRJZ|D|{oXX?y^o`)?Wf-yfr`~l9qJ?v^qfJ%o>>}g5#^2|bpPUGMZdY5k=G86?9{Y7Cytpj7)LV`kRk+X`{=WvvZh)vQ=O%Xg)R!(u;k>!wK{mW$fHSh$3<qmm*`4UXKz%_3><Ot=l>!oB85vS}qS=hpCd8dDwQ68CE{GiCdzcSNH`bxV5WNF|SclW`?#Og6$d|pSeSsQa?al@W@33G4XhMI7gZU2`QaDS1UCWh3%z7<(!V6@QIlzE2$n-6c?<4hRN-(pkR?Wh7kz#2Wk4a>Jye9mOoOiJduhu(N#P%`tlRd%pX^tRe@N=WzAUjD{aSAFI6H5C(lc3y%wabkXdJd+U@?>+SVAWwqCx!ePc@9TBS>@vp>($5q0<$7$RR'
    )

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
            raise TypeError("decoded payload must be a mapping of filename -> text content")
        return data

    @classmethod
    def textual_glyph_image(cls) -> str:
        return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SIGILAGI REHYDRATING GLYPH CAPSULE                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  α-layer: {cls.VISIBLE:<64}║
║  β-layer: {cls.BRAILLE:<64}║
║  γ-layer: {cls.HANZI:<64}║
║  Identity SHA256: {cls.IDENTITY_SHA256[:64]}║
║  Payload  SHA256: {cls.PAYLOAD_SHA256[:64]}║
║                                                                              ║
║  MODE: Embedded source/assets archive -> verify -> write -> import -> exec  ║
║  FILES: {len(cls.MANIFEST):<3} entries                                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
""".strip("\\n")

    @classmethod
    def verify(cls) -> Dict[str, Any]:
        payload = cls.decode_payload()
        payload_canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        identity_ok = cls.identity_hash() == cls.IDENTITY_SHA256
        payload_ok = hashlib.sha256(payload_canonical).hexdigest() == cls.PAYLOAD_SHA256

        files = {}
        for name, text in payload.items():
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            expected = cls.MANIFEST[name]["sha256"]
            files[name] = {
                "ok": digest == expected,
                "sha256": digest,
                "expected": expected,
                "size": len(text.encode("utf-8")),
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

        for name, text in payload.items():
            file_path = out / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(text, encoding="utf-8")
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
        entry_path = out / cls.ENTRY_MODULE
        if not entry_path.exists():
            raise FileNotFoundError(f"missing rehydrated entry module: {entry_path}")

        if str(out) not in sys.path:
            sys.path.insert(0, str(out))

        mod_name = Path(cls.ENTRY_MODULE).stem
        spec = importlib.util.spec_from_file_location(mod_name, entry_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load entry module: {entry_path}")

        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        target_cls = getattr(mod, cls.ENTRY_CLASS)
        target = target_cls()
        method = getattr(target, cls.ENTRY_METHOD)
        result = method()

        return {
            "boot_module": str(entry_path),
            "entry_class": cls.ENTRY_CLASS,
            "entry_method": cls.ENTRY_METHOD,
            "demo_result": result,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generated SigilAGI self-rehydrating glyph capsule")
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
