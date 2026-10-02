"use client";
import dynamic from "next/dynamic";
import {ArrowDown,Move3d} from "lucide-react";
import {useEffect,useRef} from "react";
import gsap from "gsap";

const ForgeScene=dynamic(()=>import("./scenes/ForgeScene"),{ssr:false});

export default function Hero(){
  const root=useRef<HTMLElement>(null);

  useEffect(()=>{
    const ctx=gsap.context(()=>{
      gsap.from(".heroWord",{
        y:92,
        opacity:0,
        rotateX:-16,
        stagger:.07,
        duration:.9,
        ease:"power4.out"
      });
      gsap.from(".heroKicker,.heroIntro,.heroSpecs,.primary",{
        y:18,
        opacity:0,
        stagger:.07,
        duration:.58,
        delay:.28,
        ease:"power3.out"
      });
      gsap.from(".heroScene",{
        scale:.9,
        opacity:0,
        duration:.95,
        delay:.16,
        ease:"power3.out"
      });
      gsap.from(".eyebrow,.dragHint,.scrollHint,.heroIndex",{
        opacity:0,
        y:8,
        stagger:.05,
        duration:.42,
        delay:.62
      });
    },root);

    const finePointer=window.matchMedia(
      "(pointer:fine) and (prefers-reduced-motion:no-preference)"
    ).matches;

    if(!finePointer){
      return()=>ctx.revert();
    }

    const scene=root.current?.querySelector(".heroScene");
    const title=root.current?.querySelector(".heroEditorial");

    const sceneX=scene?gsap.quickTo(scene,"x",{duration:.55,ease:"power3.out"}):null;
    const sceneY=scene?gsap.quickTo(scene,"y",{duration:.55,ease:"power3.out"}):null;
    const titleX=title?gsap.quickTo(title,"x",{duration:.7,ease:"power3.out"}):null;

    let frame=0;
    let latestX=0;
    let latestY=0;

    const flush=()=>{
      frame=0;
      const nx=latestX/window.innerWidth-.5;
      const ny=latestY/window.innerHeight-.5;
      sceneX?.(nx*10);
      sceneY?.(ny*7);
      titleX?.(nx*-3);
    };

    const move=(e:PointerEvent)=>{
      latestX=e.clientX;
      latestY=e.clientY;
      if(!frame) frame=requestAnimationFrame(flush);
    };

    window.addEventListener("pointermove",move,{passive:true});

    return()=>{
      window.removeEventListener("pointermove",move);
      if(frame) cancelAnimationFrame(frame);
      ctx.revert();
    };
  },[]);

  return <section className="hero" ref={root}>
    <div className="heroGrid"/>
    <div className="colorOrb orbOne"/>
    <div className="colorOrb orbTwo"/>
    <div className="colorOrb orbThree"/>
    <div className="colorOrb orbFour"/>

    <div className="eyebrow">
      <span className="pulse"/>
      IMAGE-TO-3D SYSTEM / PF-01
    </div>

    <div className="heroEditorial">
      <div className="heroKicker">AI RECONSTRUCTION FOR PHYSICAL FORM</div>

      <h1>
        <span className="heroLine">
          <span className="heroWord pixelWord">PIXELS</span>
        </span>
        <span className="heroLine heroLineRight">
          <span className="heroWord becomeWord">BECOME</span>
        </span>
        <span className="heroLine">
          <span className="heroWord objectWord">OBJECTS.</span>
        </span>
      </h1>
    </div>

    <div className="heroIntro">
      <p>
        Turn one image or a full multi-view set into usable 3D geometry.
        Preview, refine and export as textured GLB or print-ready STL.
      </p>
      <a href="#studio" className="primary">
        ENTER THE FORGE
        <span>↗</span>
      </a>
    </div>

    <div className="heroGhost" aria-hidden="true">FORGE</div>

    <div className="heroScene">
      <ForgeScene/>
    </div>

    <div className="heroSpecs">
      <article>
        <span>INPUT</span>
        <strong>1–6 VIEWS</strong>
        <small>Cloudinary or local images</small>
      </article>
      <article>
        <span>OUTPUT</span>
        <strong>GLB / STL</strong>
        <small>Color or geometry-only export</small>
      </article>
      <article>
        <span>ENGINE</span>
        <strong>DIRECT 3D</strong>
        <small>Fast or standard generation</small>
      </article>
    </div>

    <div className="dragHint">
      <Move3d size={16}/>
      <span>DRAG THE FORM</span>
    </div>

    <div className="scrollHint">
      <ArrowDown size={15}/>
      <span>SCROLL TO EXPLORE</span>
    </div>

    <div className="heroIndex">
      PF
      <br/>
      <span>01 / 03</span>
    </div>

    <div className="heroTicker">
      <span>PIXEL FORGE · IMAGE → GEOMETRY · MULTI-VIEW → FORM · GLB · STL · </span>
      <span>PIXEL FORGE · IMAGE → GEOMETRY · MULTI-VIEW → FORM · GLB · STL · </span>
    </div>
  </section>
}
