"use client";

import dynamic from "next/dynamic";
import {useMemo,useState} from "react";
import {CheckCircle2,Cloud,Download,Loader2,SlidersHorizontal,Sparkles,Upload} from "lucide-react";

const StudioScene=dynamic(()=>import("./scenes/StudioScene"),{ssr:false});

type OutputChoice="stl"|"glb"|"litho";
type PipelineState="ready"|"analyzing"|"converting"|"done"|"error";

const API_BASE=(process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000").replace(/\/$/,"");
const CLOUDINARY_CLOUD_NAME=process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME||"";
const CLOUDINARY_UPLOAD_PRESET=process.env.NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET||"";

export default function Studio(){
  const [depth,setDepth]=useState(48);
  const [detail,setDetail]=useState(72);
  const [smooth,setSmooth]=useState(35);
  const [wire,setWire]=useState(false);
  const [sourceFile,setSourceFile]=useState<File|null>(null);
  const [cloudinaryUrl,setCloudinaryUrl]=useState("");
  const [cloudinaryPublicId,setCloudinaryPublicId]=useState("");
  const [description,setDescription]=useState("");
  const [choice,setChoice]=useState<OutputChoice>("stl");
  const [pipeline,setPipeline]=useState<PipelineState>("ready");
  const [message,setMessage]=useState("READY");
  const [downloadUrl,setDownloadUrl]=useState<string|null>(null);

  const resolution=useMemo(()=>Math.max(32,Math.min(256,Math.round(64+(detail/100)*192))),[detail]);
  const depthMm=useMemo(()=>Math.max(1,Math.round((depth/100)*18*10)/10),[depth]);

  async function getWorkingFile(){
    if(sourceFile) return sourceFile;
    if(!cloudinaryUrl) return null;

    const response=await fetch(cloudinaryUrl);
    if(!response.ok) throw new Error("Could not read Cloudinary asset.");
    const blob=await response.blob();
    return new File([blob],cloudinaryPublicId||"cloudinary-source",{
      type:blob.type||"image/jpeg"
    });
  }

  function openCloudinary(){
    if(!CLOUDINARY_CLOUD_NAME||!CLOUDINARY_UPLOAD_PRESET){
      setPipeline("error");
      setMessage("ADD CLOUDINARY ENV VARS");
      return;
    }

    const cloudinary=(window as any).cloudinary;
    if(!cloudinary?.createUploadWidget){
      setPipeline("error");
      setMessage("CLOUDINARY WIDGET LOADING");
      return;
    }

    const widget=cloudinary.createUploadWidget(
      {
        cloudName:CLOUDINARY_CLOUD_NAME,
        uploadPreset:CLOUDINARY_UPLOAD_PRESET,
        sources:["local","url","camera"],
        multiple:false,
        resourceType:"image",
        folder:"pixel-forge/source-images",
        clientAllowedFormats:["png","jpg","jpeg","webp"],
        maxFileSize:8*1024*1024,
        cropping:false,
        showAdvancedOptions:false,
        styles:{
          palette:{
            window:"#11111c",
            sourceBg:"#171726",
            windowBorder:"#ffd400",
            tabIcon:"#ffd400",
            inactiveTabIcon:"#8e8e9b",
            menuIcons:"#ffd400",
            link:"#57e6ff",
            action:"#ff2d2d",
            inProgress:"#ffd400",
            complete:"#57e6ff",
            error:"#ff5d5d",
            textDark:"#11111c",
            textLight:"#ffffff"
          }
        }
      },
      (error:any,result:any)=>{
        if(error){
          setPipeline("error");
          setMessage("CLOUDINARY UPLOAD ERROR");
          return;
        }

        if(result?.event==="success"){
          setCloudinaryUrl(result.info.secure_url||"");
          setCloudinaryPublicId(result.info.public_id||"cloudinary-source");
          setSourceFile(null);
          setDownloadUrl(null);
          setPipeline("done");
          setMessage("CLOUDINARY READY");
          widget.close();
        }
      }
    );

    widget.open();
  }

  async function enhanceInput(){
    setPipeline("analyzing");
    setMessage("ANALYZING");
    setDownloadUrl(null);

    try{
      const file=await getWorkingFile();
      if(!file) throw new Error("Add an image first.");

      const body=new FormData();
      body.append("file",file);
      body.append("provider","auto");
      body.append("description",description);

      const response=await fetch(`${API_BASE}/api/v1/analysis/image`,{method:"POST",body});
      const data=await response.json();
      if(!response.ok) throw new Error(data?.detail||"Image analysis failed.");
      const prompt=data?.analysis?.generation_prompt;
      if(prompt) setDescription(prompt);
      setPipeline("done");
      setMessage(`${String(data?.provider||"AI").toUpperCase()} ANALYSIS READY`);
    }catch(error){
      setPipeline("error");
      setMessage(error instanceof Error?error.message.toUpperCase().slice(0,36):"ANALYSIS ERROR");
    }
  }

  async function exportModel(){
    setPipeline("converting");
    setMessage("BUILDING MESH");
    setDownloadUrl(null);

    try{
      const file=await getWorkingFile();
      if(!file) throw new Error("Add an image first.");

      const mode=choice==="litho"?"lithophane":"relief";
      const outputFormat=choice==="glb"?"glb":"stl";

      const body=new FormData();
      body.append("file",file);
      body.append("mode",mode);
      body.append("output_format",outputFormat);
      body.append("width_mm","100");
      body.append("depth_mm",String(depthMm));
      body.append("base_thickness_mm",choice==="litho"?"0.8":"1.5");
      body.append("max_thickness_mm","4");
      body.append("resolution",String(resolution));
      body.append("smoothing",String(smooth));
      body.append("invert","false");

      const response=await fetch(`${API_BASE}/api/v1/convert/local`,{method:"POST",body});
      const data=await response.json();
      if(!response.ok) throw new Error(data?.detail||"Conversion failed.");

      const fileUrl=String(data.file_url||"");
      setDownloadUrl(fileUrl||null);
      setPipeline("done");
      setMessage(data.watertight?"WATERTIGHT · READY":"MODEL READY");

      if(fileUrl){
        const anchor=document.createElement("a");
        anchor.href=fileUrl;
        anchor.target="_blank";
        anchor.rel="noopener noreferrer";
        anchor.click();
      }
    }catch(error){
      setPipeline("error");
      setMessage(error instanceof Error?error.message.toUpperCase().slice(0,36):"CONVERSION ERROR");
    }
  }

  const busy=pipeline==="analyzing"||pipeline==="converting";
  const hasSource=Boolean(sourceFile||cloudinaryUrl);

  return <section className="studioWrap" id="studio">
    <div className="studioTitle">
      <span>PIXEL FORGE / STUDIO</span>
      <span className="ready">{busy?"◌":"●"} CLOUDINARY + GEMINI + MESH</span>
    </div>

    <div className="studio">
      <aside className="panel source">
        <div className="panelLabel"><Upload size={14}/> SOURCE</div>

        <button className="cloudinaryUpload" onClick={openCloudinary} disabled={busy}>
          <Cloud size={15}/>
          {cloudinaryUrl?"REPLACE CLOUDINARY ASSET":"UPLOAD WITH CLOUDINARY"}
        </button>

        {cloudinaryUrl&&<a
          className="cloudinaryAsset"
          href={cloudinaryUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          CLOUDINARY ASSET READY ↗
        </a>}

        <label className="drop">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={e=>{
              const next=e.target.files?.[0]||null;
              setSourceFile(next);
              if(next){
                setCloudinaryUrl("");
                setCloudinaryPublicId("");
              }
              setDownloadUrl(null);
              setPipeline("ready");
              setMessage(next?"LOCAL IMAGE LOADED":"READY");
            }}
          />
          <span className="plus">{hasSource?"✓":"+"}</span>
          <strong>{sourceFile?.name||(cloudinaryUrl?"CLOUDINARY IMAGE":"DROP LOCAL IMAGE")}</strong>
          <small>CLOUDINARY PREFERRED · LOCAL FALLBACK · MAX 8MB</small>
        </label>

        <label className="fieldLabel">DESCRIBE YOUR FORM</label>
        <textarea
          value={description}
          onChange={e=>setDescription(e.target.value)}
          placeholder="A raised relief with a clean flat base..."
        />

        <button className="enhance" onClick={enhanceInput} disabled={busy}>
          {pipeline==="analyzing"?<Loader2 size={14} className="spin"/>:<Sparkles size={14}/>}
          {pipeline==="analyzing"?"GEMINI ANALYZING":"ENHANCE WITH GEMINI"}
        </button>

        <div className="status">
          <span>MEDIA PIPELINE</span>
          <b className={pipeline==="error"?"error":""}>{message}</b>
        </div>
      </aside>

      <div className="viewport">
        <StudioScene depth={depth} wire={wire}/>
        <div className="viewTop">
          <span>LIVE GEOMETRY</span>
          <span>{resolution} × {resolution}</span>
        </div>
        <button className="wireBtn" onClick={()=>setWire(!wire)}>{wire?"SOLID":"WIREFRAME"}</button>
        <div className="axis">X&nbsp;&nbsp;Y&nbsp;&nbsp;Z</div>
      </div>

      <aside className="panel controls">
        <div className="panelLabel"><SlidersHorizontal size={14}/> PARAMETERS</div>
        <Control name="DEPTH" value={depth} set={setDepth}/>
        <Control name="DETAIL" value={detail} set={setDetail}/>
        <Control name="SMOOTH" value={smooth} set={setSmooth}/>

        <div className="dimension">
          <span>MODEL SIZE</span>
          <strong>100 mm · DEPTH {depthMm} mm · RES {resolution}</strong>
        </div>

        <div className="formats">
          <button className={choice==="stl"?"active":""} onClick={()=>setChoice("stl")}>STL</button>
          <button className={choice==="glb"?"active":""} onClick={()=>setChoice("glb")}>GLB</button>
          <button className={choice==="litho"?"active":""} onClick={()=>setChoice("litho")}>LITHO</button>
        </div>

        <button className="export" onClick={exportModel} disabled={busy}>
          {pipeline==="converting"?<Loader2 size={15} className="spin"/>:downloadUrl?<CheckCircle2 size={15}/>:<Download size={15}/>}
          {pipeline==="converting"?"GENERATING MODEL":downloadUrl?"DOWNLOAD AGAIN":"EXPORT MODEL"}
        </button>

        {downloadUrl&&<a className="resultLink" href={downloadUrl} target="_blank" rel="noopener noreferrer">OPEN GENERATED FILE ↗</a>}
      </aside>
    </div>
  </section>
}

function Control({name,value,set}:{name:string,value:number,set:(n:number)=>void}){
  return <label className="control">
    <span><b>{name}</b><em>{value}</em></span>
    <input type="range" min="0" max="100" value={value} onChange={e=>set(Number(e.target.value))}/>
  </label>
}
