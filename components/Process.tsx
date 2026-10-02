"use client";
import {useEffect,useRef} from "react";
import gsap from "gsap";
import {ScrollTrigger} from "gsap/ScrollTrigger";

const stages=[
  ["01","CAPTURE","Upload one clean reference or a multi-view set of up to six photos."],
  ["02","UNDERSTAND","The pipeline prepares each view and keeps the subject consistent across angles."],
  ["03","RECONSTRUCT","Direct image-to-3D generation builds a complete 360° mesh from the references."],
  ["04","EXPORT","Choose textured GLB or full 3D STL with color removed for fabrication workflows."]
];

export default function Process(){
  const root=useRef<HTMLElement>(null);

  useEffect(()=>{
    gsap.registerPlugin(ScrollTrigger);
    const ctx=gsap.context(()=>{
      gsap.from(".processStatement",{
        scrollTrigger:{trigger:root.current,start:"top 72%"},
        y:70,
        opacity:0,
        duration:1,
        ease:"power4.out"
      });
      gsap.from(".stage",{
        scrollTrigger:{trigger:".stageRail",start:"top 80%"},
        y:48,
        opacity:0,
        stagger:.12,
        duration:.72,
        ease:"power3.out"
      });
      gsap.to(".stageGlyph",{
        scrollTrigger:{
          trigger:".stageRail",
          start:"top bottom",
          end:"bottom top",
          scrub:1
        },
        rotate:14,
        y:-14,
        stagger:.04
      });
    },root);

    return()=>ctx.revert();
  },[]);

  return <section className="process" id="process" ref={root}>
    <div className="processAura auraA"/>
    <div className="processAura auraB"/>

    <div className="processIntro">
      <span className="processLabel">THE SYSTEM / 02</span>
      <p>
        A single continuous pipeline from photographed matter to editable,
        downloadable geometry.
      </p>
    </div>

    <div className="processStatement">
      <h2>
        FROM FLAT
        <br/>
        MEDIA TO
        <br/>
        <i>REAL FORM.</i>
      </h2>
      <div className="processAside">
        <strong>ONE SUBJECT.</strong>
        <strong>MULTIPLE VIEWS.</strong>
        <strong>ONE COHERENT MODEL.</strong>
      </div>
    </div>

    <div className="stageRail">
      {stages.map((s,i)=>
        <article className={"stage stage"+i} key={s[0]}>
          <div className="stageTop">
            <span>{s[0]}</span>
            <span>{i===3?"●":"○"}</span>
          </div>
          <div className={"stageGlyph g"+i}><div/></div>
          <h3>{s[1]}</h3>
          <p>{s[2]}</p>
        </article>
      )}
    </div>
  </section>
}
