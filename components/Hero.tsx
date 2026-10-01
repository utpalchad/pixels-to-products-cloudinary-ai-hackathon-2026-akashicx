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
      gsap.from(".heroWord",{y:130,opacity:0,rotateX:-32,stagger:.095,duration:1.05,ease:"power4.out"});
      gsap.from(".heroCopy p",{y:24,opacity:0,duration:.72,delay:.44,ease:"power3.out"});
      gsap.from(".heroMetaRow",{y:18,opacity:0,duration:.62,delay:.58,ease:"power3.out"});
      gsap.from(".primary",{scale:.9,opacity:0,duration:.65,delay:.68,ease:"back.out(1.7)"});
      gsap.from(".eyebrow,.dragHint,.scrollHint,.heroIndex",{opacity:0,y:10,stagger:.07,duration:.55,delay:.82});
      gsap.to(".heroScene",{y:-12,duration:3.6,ease:"sine.inOut",repeat:-1,yoyo:true});
    },root);

    const heading=root.current?.querySelector(".heroCopy h1");
    const copy=root.current?.querySelector(".heroCopy p");
    const xTo=heading?gsap.quickTo(heading,"x",{duration:.65,ease:"power3.out"}):null;
    const yTo=heading?gsap.quickTo(heading,"y",{duration:.65,ease:"power3.out"}):null;
    const copyX=copy?gsap.quickTo(copy,"x",{duration:.8,ease:"power3.out"}):null;

    const move=(e:PointerEvent)=>{
      const nx=e.clientX/window.innerWidth-.5;
      const ny=e.clientY/window.innerHeight-.5;
      xTo?.(nx*14);
      yTo?.(ny*8);
      copyX?.(nx*7);
    };

    window.addEventListener("pointermove",move,{passive:true});
    return()=>{
      window.removeEventListener("pointermove",move);
      ctx.revert();
    };
  },[]);

  return <section className="hero" ref={root}>
    <div className="heroGrid"/>
    <div className="colorOrb orbOne"/>
    <div className="colorOrb orbTwo"/>
    <div className="colorOrb orbThree"/>
    <div className="colorOrb orbFour"/>

    <div className="eyebrow"><span className="pulse"/>IMAGE → GEOMETRY / 001</div>

    <div className="heroCopy">
      <h1>
        <span className="heroLine"><span className="heroWord">TURN</span></span>
        <span className="heroLine"><span className="heroWord chroma">PIXELS</span></span>
        <span className="heroLine"><span className="heroWord">INTO <b className="hotWord">FORM.</b></span></span>
      </h1>

      <div className="heroMetaRow">
        <span><i className="dot redDot"/>LIVE 3D</span>
        <span><i className="dot yellowDot"/>STL / GLB / LITHO</span>
      </div>

      <p>Transform ordinary images into tactile digital geometry. Shape depth, explore the mesh, export the object.</p>
      <a href="#studio" className="primary">ENTER THE FORGE <span>↗</span></a>
    </div>

    <div className="heroScene"><ForgeScene/></div>
    <div className="dragHint"><Move3d size={17}/><span>DRAG TO EXPLORE</span></div>
    <div className="scrollHint"><ArrowDown size={16}/><span>SCROLL TO DECONSTRUCT</span></div>
    <div className="heroIndex">PF<br/><span>01—04</span></div>

    <div className="heroTicker">
      <span>PIXEL FORGE · IMAGE TO DEPTH · DEPTH TO MESH · MESH TO FORM · </span>
      <span>PIXEL FORGE · IMAGE TO DEPTH · DEPTH TO MESH · MESH TO FORM · </span>
    </div>
  </section>
}
