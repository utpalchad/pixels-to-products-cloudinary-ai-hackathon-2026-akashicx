"use client";

import dynamic from "next/dynamic";
import {useMemo,useState} from "react";
import {
  CheckCircle2,
  Cloud,
  Download,
  Loader2,
  SlidersHorizontal,
  Sparkles,
  Upload
} from "lucide-react";

const StudioScene=dynamic(()=>import("./scenes/StudioScene"),{ssr:false});

type ModelMode="relief"|"lithophane"|"full3d";
type OutputFormat="stl"|"glb";
type PipelineState="ready"|"analyzing"|"converting"|"done"|"error";

const API_BASE=(process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000").replace(/\/$/,"");
const CLOUDINARY_CLOUD_NAME=process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME||"";
const CLOUDINARY_UPLOAD_PRESET=process.env.NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET||"";

const wait=(ms:number)=>new Promise(resolve=>window.setTimeout(resolve,ms));

export default function Studio(){
  const [depth,setDepth]=useState(48);
  const [detail,setDetail]=useState(72);
  const [smooth,setSmooth]=useState(35);
  const [wire,setWire]=useState(false);
  const [sourceFile,setSourceFile]=useState<File|null>(null);
  const [cloudinaryUrl,setCloudinaryUrl]=useState("");
  const [cloudinaryPublicId,setCloudinaryPublicId]=useState("");
  const [description,setDescription]=useState("");
  const [modelMode,setModelMode]=useState<ModelMode>("relief");
  const [outputFormat,setOutputFormat]=useState<OutputFormat>("stl");
  const [pipeline,setPipeline]=useState<PipelineState>("ready");
  const [message,setMessage]=useState("READY");
  const [downloadUrl,setDownloadUrl]=useState<string|null>(null);
  const [viewerUrl,setViewerUrl]=useState<string|null>(null);

  const resolution=useMemo(
    ()=>Math.max(32,Math.min(256,Math.round(64+(detail/100)*192))),
    [detail]
  );
  const depthMm=useMemo(
    ()=>Math.max(1,Math.round((depth/100)*18*10)/10),
    [depth]
  );

  function clearResult(nextMessage?:string){
    setDownloadUrl(null);
    setViewerUrl(null);
    if(nextMessage) setMessage(nextMessage);
  }

  async function getWorkingFile(){
    if(sourceFile) return sourceFile;
    if(!cloudinaryUrl) return null;

    const response=await fetch(cloudinaryUrl);
    if(!response.ok) throw new Error("Could not read Cloudinary asset.");
    const blob=await response.blob();

    return new File(
      [blob],
      cloudinaryPublicId||"cloudinary-source",
      {type:blob.type||"image/jpeg"}
    );
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
          clearResult("CLOUDINARY READY");
          setPipeline("done");
          widget.close();
        }
      }
    );

    widget.open();
  }

  async function enhanceInput(){
    setPipeline("analyzing");
    setMessage("ANALYZING");
    clearResult();

    try{
      const file=await getWorkingFile();
      if(!file) throw new Error("Add an image first.");

      const body=new FormData();
      body.append("file",file);
      body.append("provider","auto");
      body.append("description",description);

      const response=await fetch(`${API_BASE}/api/v1/analysis/image`,{
        method:"POST",
        body
      });
      const data=await response.json();

      if(!response.ok){
        throw new Error(data?.detail||"Image analysis failed.");
      }

      const prompt=data?.analysis?.generation_prompt;
      if(prompt) setDescription(prompt);

      setPipeline("done");
      setMessage(`${String(data?.provider||"AI").toUpperCase()} ANALYSIS READY`);
    }catch(error){
      setPipeline("error");
      setMessage(
        error instanceof Error
          ?error.message.toUpperCase().slice(0,120)
          :"ANALYSIS ERROR"
      );
    }
  }

  async function finishFull3D(job:any){
    if(!job?.id) throw new Error("3D job did not return an id.");

    setDownloadUrl(`${API_BASE}/api/v1/jobs/${job.id}/download`);
    setViewerUrl(String(job.viewer_url||job.glb_url||"")||null);
    setPipeline("done");
    setMessage("FULL 3D → TEXTURED GLB READY");
  }

  async function pollFull3D(jobId:string){
    for(let attempt=0;attempt<36;attempt++){
      await wait(5000);

      const response=await fetch(`${API_BASE}/api/v1/jobs/${jobId}`);
      const job=await response.json();

      if(!response.ok){
        throw new Error(job?.detail||"Could not check 3D generation status.");
      }

      if(job.status==="done"&&job.glb_url){
        await finishFull3D(job);
        return;
      }

      if(job.status==="failed"){
        throw new Error(job.error||"Full 3D generation failed.");
      }

      const progress=Number(job.progress||Math.min((attempt+1)*10,90));
      setMessage(`FULL 3D GENERATING · ${progress}%`);
    }

    throw new Error("Full 3D generation timed out. Try again.");
  }

  async function generateFull3D(){
    setPipeline("converting");
    setMessage("GEMINI → FULL 3D");
    clearResult();

    const body=new FormData();

    if(cloudinaryUrl){
      body.append("cloudinary_urls",cloudinaryUrl);
    }else{
      const file=await getWorkingFile();
      if(!file) throw new Error("Add an image first.");
      body.append("files",file);
    }

    body.append("vision_provider","auto");
    body.append("description",description);
    body.append("tier","draft");
    body.append("analyze_image","true");

    const response=await fetch(`${API_BASE}/api/v1/ai3d/generate`,{
      method:"POST",
      body
    });
    const job=await response.json();

    if(!response.ok){
      throw new Error(job?.detail||"Full 3D generation failed.");
    }

    if(job.status==="done"&&job.glb_url){
      await finishFull3D(job);
      return;
    }

    setMessage("FULL 3D QUEUED");
    await pollFull3D(String(job.id));
  }

  async function exportLocalModel(){
    const file=await getWorkingFile();
    if(!file) throw new Error("Add an image first.");

    const body=new FormData();
    body.append("file",file);
    body.append("mode",modelMode);
    body.append("output_format",outputFormat);
    body.append("width_mm","100");
    body.append("depth_mm",String(depthMm));
    body.append(
      "base_thickness_mm",
      modelMode==="lithophane"?"0.8":"1.5"
    );
    body.append("max_thickness_mm","4");
    body.append("resolution",String(resolution));
    body.append("smoothing",String(smooth));
    body.append("invert","false");

    const response=await fetch(`${API_BASE}/api/v1/convert/local`,{
      method:"POST",
      body
    });
    const data=await response.json();

    if(!response.ok){
      throw new Error(data?.detail||"Conversion failed.");
    }

    const fileUrl=String(data.download_url||data.file_url||"");
    setDownloadUrl(fileUrl||null);
    setViewerUrl(null);
    setPipeline("done");

    const resultMode=String(data.mode||modelMode).toUpperCase();
    const resultFormat=String(data.format||outputFormat).toUpperCase();
    setMessage(`${resultMode} → ${resultFormat} READY`);
  }

  async function exportModel(){
    setPipeline("converting");
    setMessage(modelMode==="full3d"?"GENERATING FULL 3D":"BUILDING MESH");
    clearResult();

    try{
      if(modelMode==="full3d"){
        await generateFull3D();
      }else{
        await exportLocalModel();
      }
    }catch(error){
      setPipeline("error");
      setMessage(
        error instanceof Error
          ?error.message.toUpperCase().slice(0,120)
          :"GENERATION ERROR"
      );
    }
  }

  const busy=pipeline==="analyzing"||pipeline==="converting";
  const hasSource=Boolean(sourceFile||cloudinaryUrl);
  const full3D=modelMode==="full3d";

  return <section className="studioWrap" id="studio">
    <div className="studioTitle">
      <span>PIXEL FORGE / STUDIO</span>
      <span className="ready">
        {busy?"◌":"●"} CLOUDINARY + GEMINI + 3D
      </span>
    </div>

    <div className="studio">
      <aside className="panel source">
        <div className="panelLabel"><Upload size={14}/> SOURCE</div>

        <button
          className="cloudinaryUpload"
          onClick={openCloudinary}
          disabled={busy}
        >
          <Cloud size={15}/>
          {cloudinaryUrl
            ?"REPLACE CLOUDINARY ASSET"
            :"UPLOAD WITH CLOUDINARY"}
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

              clearResult(next?"LOCAL IMAGE LOADED":"READY");
              setPipeline("ready");
            }}
          />
          <span className="plus">{hasSource?"✓":"+"}</span>
          <strong>
            {sourceFile?.name||
              (cloudinaryUrl?"CLOUDINARY IMAGE":"DROP LOCAL IMAGE")}
          </strong>
          <small>CLOUDINARY PREFERRED · LOCAL FALLBACK · MAX 8MB</small>
        </label>

        <label className="fieldLabel">DESCRIBE YOUR FORM</label>
        <textarea
          value={description}
          onChange={e=>setDescription(e.target.value)}
          placeholder="Describe the object, materials, colors, and shape..."
        />

        <button
          className="enhance"
          onClick={enhanceInput}
          disabled={busy}
        >
          {pipeline==="analyzing"
            ?<Loader2 size={14} className="spin"/>
            :<Sparkles size={14}/>}
          {pipeline==="analyzing"
            ?"GEMINI ANALYZING"
            :"ENHANCE WITH GEMINI"}
        </button>

        <div className="status">
          <span>MEDIA PIPELINE</span>
          <b className={pipeline==="error"?"error":""}>{message}</b>
        </div>
      </aside>

      <div className="viewport">
        <StudioScene depth={depth} wire={wire}/>
        <div className="viewTop">
          <span>{full3D?"AI FULL 3D":"LIVE GEOMETRY"}</span>
          <span>{full3D?"TEXTURED GLB":`${resolution} × ${resolution}`}</span>
        </div>
        <button className="wireBtn" onClick={()=>setWire(!wire)}>
          {wire?"SOLID":"WIREFRAME"}
        </button>
        <div className="axis">X&nbsp;&nbsp;Y&nbsp;&nbsp;Z</div>
      </div>

      <aside className="panel controls">
        <div className="panelLabel">
          <SlidersHorizontal size={14}/> PARAMETERS
        </div>

        {!full3D&&<>
          <Control name="DEPTH" value={depth} set={setDepth}/>
          <Control name="DETAIL" value={detail} set={setDetail}/>
          <Control name="SMOOTH" value={smooth} set={setSmooth}/>

          <div className="dimension">
            <span>MODEL SIZE</span>
            <strong>
              100 mm · DEPTH {depthMm} mm · RES {resolution}
            </strong>
          </div>
        </>}

        <div className="dimension">
          <span>MODEL ENGINE</span>
          <strong>
            {modelMode==="full3d"
              ?"GEMINI → 360° TEXTURED AI MODEL"
              :modelMode==="relief"
                ?"2.5D HEIGHT-MAP RELIEF"
                :"THICKNESS-BASED LITHOPHANE"}
          </strong>
        </div>

        <label className="fieldLabel">MODEL TYPE</label>
        <div className="formats">
          <button
            className={modelMode==="relief"?"active":""}
            onClick={()=>{
              setModelMode("relief");
              clearResult("RELIEF (2.5D) SELECTED");
            }}
          >
            RELIEF
          </button>
          <button
            className={modelMode==="lithophane"?"active":""}
            onClick={()=>{
              setModelMode("lithophane");
              clearResult("LITHOPHANE SELECTED");
            }}
          >
            LITHO
          </button>
          <button
            className={modelMode==="full3d"?"active":""}
            onClick={()=>{
              setModelMode("full3d");
              setOutputFormat("glb");
              clearResult("FULL 3D (AI) SELECTED");
            }}
          >
            FULL 3D
          </button>
        </div>

        <label className="fieldLabel">EXPORT FORMAT</label>
        <div className="formats">
          {!full3D&&<button
            className={outputFormat==="stl"?"active":""}
            onClick={()=>{
              setOutputFormat("stl");
              clearResult();
            }}
          >
            STL
          </button>}
          <button
            className={outputFormat==="glb"?"active":""}
            onClick={()=>{
              setOutputFormat("glb");
              clearResult();
            }}
          >
            {full3D?"GLB · COLOR":"GLB"}
          </button>
        </div>

        {full3D&&<div className="dimension">
          <span>FULL 3D MODE</span>
          <strong>DRAFT · 360° · TEXTURED · GLB ONLY</strong>
        </div>}

        <button
          className="export"
          onClick={exportModel}
          disabled={busy}
        >
          {pipeline==="converting"
            ?<Loader2 size={15} className="spin"/>
            :downloadUrl
              ?<CheckCircle2 size={15}/>
              :<Download size={15}/>}
          {pipeline==="converting"
            ?(full3D?"GENERATING FULL 3D":"GENERATING MODEL")
            :(full3D?"GENERATE FULL 3D":"GENERATE MODEL")}
        </button>

        {downloadUrl&&<a className="resultLink" href={downloadUrl}>
          {full3D?"DOWNLOAD TEXTURED GLB ↓":`DOWNLOAD ${outputFormat.toUpperCase()} ↓`}
        </a>}

        {viewerUrl&&<a
          className="resultLink"
          href={viewerUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          VIEW FULL 3D ↗
        </a>}
      </aside>
    </div>
  </section>
}

function Control({
  name,
  value,
  set
}:{
  name:string;
  value:number;
  set:(n:number)=>void;
}){
  return <label className="control">
    <span><b>{name}</b><em>{value}</em></span>
    <input
      type="range"
      min="0"
      max="100"
      value={value}
      onChange={e=>set(Number(e.target.value))}
    />
  </label>
}
