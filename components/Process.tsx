"use client";
import {useEffect,useRef} from "react";
import gsap from "gsap";
import {ScrollTrigger} from "gsap/ScrollTrigger";

const stages=[["01","PIXEL","Your source image enters the media pipeline."],["02","DEPTH","Luminance and structure become spatial information."],["03","MESH","Depth is translated into vertices, faces and form."],["04","OBJECT","Refine, preview and export as STL or GLB."]];

export default function Process(){
  const root=useRef<HTMLElement>(null);
  useEffect(()=>{
    gsap.registerPlugin(ScrollTrigger);
    const ctx=gsap.context(()=>{
      gsap.from(".sectionHead h2",{scrollTrigger:{trigger:root.current,start:"top 72%"},y:80,opacity:0,duration:1,ease:"power4.out"});
      gsap.from(".stage",{scrollTrigger:{trigger:".stageRail",start:"top 78%"},y:70,opacity:0,stagger:.14,duration:.8,ease:"power3.out"});
      gsap.to(".stageGlyph",{scrollTrigger:{trigger:".stageRail",start:"top bottom",end:"bottom top",scrub:1},rotate:18,y:-18,stagger:.05});
    },root);
    return()=>ctx.revert();
  },[]);
  return <section className="process" id="process" ref={root}>
    <div className="processAura auraA"/><div className="processAura auraB"/>
    <div className="sectionHead"><span>THE PIPELINE</span><h2>FROM FLAT<br/>TO <i>PHYSICAL.</i></h2><p>Not four feature cards. One continuous transformation from media to geometry.</p></div>
    <div className="stageRail">{stages.map((s,i)=><article className={"stage stage"+i} key={s[0]}><div className="stageTop"><span>{s[0]}</span><span>{i===3?"●":"○"}</span></div><div className={"stageGlyph g"+i}><div/></div><h3>{s[1]}</h3><p>{s[2]}</p></article>)}</div>
  </section>
}
