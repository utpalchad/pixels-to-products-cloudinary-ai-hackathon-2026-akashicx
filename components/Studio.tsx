"use client";

import dynamic from "next/dynamic";
import {
  buildCloudinaryPrepUrl,
  buildCloudinaryPreviewUrl,
  canCloudinaryUpscale
} from "../lib/cloudinary";
import {useMemo,useRef,useState} from "react";
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
type GenerationMode="fast"|"standard";
type PipelineState="ready"|"analyzing"|"converting"|"done"|"error";
type CloudinaryView={url:string;publicId:string;width:number;height:number};

const API_BASE=(process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000").replace(/\/$/,"");
const CLOUDINARY_CLOUD_NAME=process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME||"";
const CLOUDINARY_UPLOAD_PRESET=process.env.NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET||"";

const wait=(ms:number)=>new Promise(resolve=>window.setTimeout(resolve,ms));

export default function Studio(){
  const localInputRef=useRef<HTMLInputElement|null>(null);
  const [depth,setDepth]=useState(48);
  const [detail,setDetail]=useState(72);
  const [smooth,setSmooth]=useState(35);
  const [wire,setWire]=useState(false);
  const [accurateMode,setAccurateMode]=useState(false);
  const [cloudinaryViews,setCloudinaryViews]=useState<CloudinaryView[]>([]);
  const [sourceFile,setSourceFile]=useState<File|null>(null);
  const [localFiles,setLocalFiles]=useState<File[]>([]);
  const [cloudinaryUrl,setCloudinaryUrl]=useState("");
  const [cloudinaryPublicId,setCloudinaryPublicId]=useState("");
  const [cloudinaryWidth,setCloudinaryWidth]=useState(0);
  const [cloudinaryHeight,setCloudinaryHeight]=useState(0);
  const [removeBackground,setRemoveBackground]=useState(true);
  const [restoreImage,setRestoreImage]=useState(false);
  const [upscaleImage,setUpscaleImage]=useState(false);
  const [improveImage,setImproveImage]=useState(true);
  const [description,setDescription]=useState("");
  const [modelMode,setModelMode]=useState<ModelMode>("relief");
  const [outputFormat,setOutputFormat]=useState<OutputFormat>("stl");
  const [generationMode,setGenerationMode]=useState<GenerationMode>("standard");
  const [pipeline,setPipeline]=useState<PipelineState>("ready");
  const [message,setMessage]=useState("READY");
  const [downloadUrl,setDownloadUrl]=useState<string|null>(null);
  const [viewerUrl,setViewerUrl]=useState<string|null>(null);
  const [full3DJobId,setFull3DJobId]=useState<string|null>(null);

  const resolution=useMemo(
    ()=>Math.max(32,Math.min(256,Math.round(64+(detail/100)*192))),
    [detail]
  );
  const depthMm=useMemo(
    ()=>Math.max(1,Math.round((depth/100)*18*10)/10),
    [depth]
  );

  const cloudinaryPrepOptions=useMemo(()=>({
    removeBackground,
    restore:restoreImage,
    upscale:upscaleImage,
    improve:improveImage,
    width:cloudinaryWidth,
    height:cloudinaryHeight
  }),[
    removeBackground,
    restoreImage,
    upscaleImage,
    improveImage,
    cloudinaryWidth,
    cloudinaryHeight
  ]);

  const cloudinaryPrepUrl=useMemo(
    ()=>buildCloudinaryPrepUrl(cloudinaryUrl,cloudinaryPrepOptions),
    [cloudinaryUrl,cloudinaryPrepOptions]
  );

  const cloudinaryPreviewUrl=useMemo(
    ()=>buildCloudinaryPreviewUrl(cloudinaryUrl,cloudinaryPrepOptions),
    [cloudinaryUrl,cloudinaryPrepOptions]
  );

  const cloudinaryPrepUrls=useMemo(
    ()=>cloudinaryViews.map(view=>buildCloudinaryPrepUrl(view.url,{
      removeBackground,
      restore:restoreImage,
      upscale:upscaleImage,
      improve:improveImage,
      width:view.width,
      height:view.height
    })),
    [
      cloudinaryViews,
      removeBackground,
      restoreImage,
      upscaleImage,
      improveImage
    ]
  );

  const canUpscale=canCloudinaryUpscale(cloudinaryWidth,cloudinaryHeight);

  function clearResult(nextMessage?:string){
    setDownloadUrl(null);
    setViewerUrl(null);
    setFull3DJobId(null);
    if(nextMessage) setMessage(nextMessage);
  }

  async function fetchCloudinaryReady(url:string){
    let lastStatus=0;

    for(let attempt=0;attempt<8;attempt++){
      const response=await fetch(url);
      lastStatus=response.status;

      if(response.ok) return response;

      if(response.status===420||response.status===423){
        setMessage("CLOUDINARY AI PREPROCESSING");
        await wait(Math.min(1500+attempt*500,4000));
        continue;
      }

      throw new Error(`Cloudinary preprocessing failed (${response.status}).`);
    }

    throw new Error(`Cloudinary preprocessing is still pending (${lastStatus}).`);
  }

  async function getWorkingFile(){
    if(sourceFile) return sourceFile;
    if(!cloudinaryPrepUrl) return null;

    const response=await fetchCloudinaryReady(cloudinaryPrepUrl);
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
        multiple:accurateMode,
        maxFiles:accurateMode?Math.max(1,6-cloudinaryViews.length):1,
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
          const detail=String(
            error?.statusText||
            error?.message||
            error?.status||
            ""
          ).toUpperCase();

          if(detail.includes("PRESET")){
            setPipeline("ready");
            setMessage("CLOUDINARY PRESET MISSING · OPENING LOCAL MULTI-UPLOAD");
            try{ widget.close(); }catch{}
            window.setTimeout(()=>localInputRef.current?.click(),250);
          }else{
            setPipeline("error");
            setMessage("CLOUDINARY UPLOAD ERROR · LOCAL MULTI-UPLOAD AVAILABLE");
          }
          return;
        }

        if(result?.event==="success"){
          const view:CloudinaryView={
            url:result.info.secure_url||"",
            publicId:result.info.public_id||"cloudinary-source",
            width:Number(result.info.width||0),
            height:Number(result.info.height||0)
          };

          if(accurateMode){
            setCloudinaryViews(current=>{
              if(current.some(item=>item.url===view.url)) return current;
              return [...current,view].slice(0,6);
            });
            setCloudinaryUrl(current=>current||view.url);
            setCloudinaryPublicId(current=>current||view.publicId);
            setCloudinaryWidth(current=>current||view.width);
            setCloudinaryHeight(current=>current||view.height);
            clearResult("MULTI-VIEW IMAGE ADDED");
          }else{
            setCloudinaryViews([view]);
            setCloudinaryUrl(view.url);
            setCloudinaryPublicId(view.publicId);
            setCloudinaryWidth(view.width);
            setCloudinaryHeight(view.height);
            clearResult("CLOUDINARY READY");
            widget.close();
          }

          setSourceFile(null);
          setLocalFiles([]);
          setPipeline("done");
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

    setFull3DJobId(String(job.id));
    setDownloadUrl(`${API_BASE}/api/v1/jobs/${job.id}/download`);
    setViewerUrl(String(job.viewer_url||job.glb_url||"")||null);
    setPipeline("done");
    setMessage("FULL 3D → GLB + STL READY");
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
    setMessage(generationMode==="fast"?"FAST 3D → RECONSTRUCTING":"STANDARD 3D → RECONSTRUCTING");
    clearResult();

    const body=new FormData();

    const preparedViews=accurateMode
      ?cloudinaryPrepUrls.slice(0,6)
      :(cloudinaryPrepUrl?[cloudinaryPrepUrl]:[]);

    if(preparedViews.length){
      body.append("cloudinary_urls",preparedViews.join(","));
    }else if(accurateMode&&localFiles.length){
      localFiles.slice(0,6).forEach(file=>body.append("files",file));
    }else{
      const file=await getWorkingFile();
      if(!file) throw new Error("Add an image first.");
      body.append("files",file);
    }

    body.append("vision_provider","auto");
    body.append("description",description);
    body.append("tier",generationMode==="fast"?"draft":"standard");
    body.append("analyze_image","false");

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
  const hasSource=Boolean(sourceFile||localFiles.length||cloudinaryUrl||cloudinaryViews.length);
  const full3D=modelMode==="full3d";

  return <section className="studioWrap" id="studio">
    <div className="studioTitle">
      <span>PIXEL FORGE / STUDIO</span>
      <span className="ready">
        {busy?"◌":"●"} CLOUDINARY + DIRECT IMAGE 3D
      </span>
    </div>

    <div className="studio">
      <aside className="panel source">
        <div className="panelLabel"><Upload size={14}/> SOURCE</div>

        <div className="accuracyMode">
          <div>
            <strong>MORE ACCURATE 3D</strong>
            <small>{accurateMode?"MULTI-VIEW · UP TO 6 PHOTOS":"QUICK MODE · 1 PHOTO"}</small>
          </div>
          <button
            type="button"
            className={accurateMode?"toggle on":"toggle"}
            aria-pressed={accurateMode}
            onClick={()=>{
              const next=!accurateMode;
              setAccurateMode(next);
              if(!next){
                setCloudinaryViews(current=>current.slice(0,1));
                setLocalFiles(current=>{
                  const first=current.slice(0,1);
                  setSourceFile(first[0]||null);
                  return first;
                });
              }
              clearResult(next?"MULTI-VIEW MODE ON":"QUICK MODE ON");
            }}
          >
            <span/>
          </button>
        </div>

        {accurateMode&&<div className="multiViewGuide">
          <b>{cloudinaryViews.length}/6 VIEWS</b>
          <span>FRONT · BACK · LEFT · RIGHT · TOP · EXTRA</span>
        </div>}

        <button
          className="cloudinaryUpload"
          onClick={openCloudinary}
          disabled={busy||(accurateMode&&cloudinaryViews.length>=6)}
        >
          <Cloud size={15}/>
          {accurateMode
            ?(cloudinaryViews.length>=6?"6 VIEWS READY":"ADD MULTI-VIEW PHOTOS")
            :cloudinaryUrl
              ?"REPLACE CLOUDINARY ASSET"
              :"UPLOAD WITH CLOUDINARY"}
        </button>

        {accurateMode&&cloudinaryViews.length>1&&<div className="multiViewList">
          {cloudinaryViews.map((view,index)=><a
            key={view.url}
            href={view.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            VIEW {index+1}
          </a>)}
        </div>}

        {cloudinaryUrl&&<>
          <a
            className="cloudinaryAsset"
            href={cloudinaryUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            ORIGINAL CLOUDINARY ASSET ↗
          </a>

          <label className="fieldLabel">CLOUDINARY AI PREP</label>
          <div className="cloudinaryTools">
            <button
              className={removeBackground?"active":""}
              onClick={()=>{
                setRemoveBackground(!removeBackground);
                clearResult("CLOUDINARY PREP UPDATED");
              }}
            >
              BG REMOVE
            </button>
            <button
              className={improveImage?"active":""}
              onClick={()=>{
                setImproveImage(!improveImage);
                clearResult("CLOUDINARY PREP UPDATED");
              }}
            >
              IMPROVE
            </button>
            <button
              className={restoreImage?"active":""}
              onClick={()=>{
                setRestoreImage(!restoreImage);
                clearResult("CLOUDINARY PREP UPDATED");
              }}
            >
              RESTORE
            </button>
            <button
              className={upscaleImage?"active":""}
              disabled={!canUpscale}
              onClick={()=>{
                setUpscaleImage(!upscaleImage);
                clearResult("CLOUDINARY PREP UPDATED");
              }}
            >
              UPSCALE 4×
            </button>
          </div>

          <div className="cloudinaryPrepMeta">
            AI INPUT: {removeBackground?"BG REMOVED · ":""}
            {improveImage?"IMPROVED · ":""}
            {restoreImage?"RESTORED · ":""}
            {upscaleImage&&canUpscale?"4× UPSCALED":"ORIGINAL RES"}
            {!canUpscale&&cloudinaryWidth>0
              ?" · UPSCALE UNAVAILABLE ABOVE 4.2MP"
              :""}
          </div>

          <a
            className="cloudinaryProcessed"
            href={cloudinaryPreviewUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            VIEW PREPROCESSED IMAGE ↗
          </a>
        </>}

        <label className="drop">
          <input
            ref={localInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple={accurateMode}
            onChange={e=>{
              const selected=Array.from(e.target.files||[]);
              const nextFiles=(accurateMode?selected.slice(0,6):selected.slice(0,1));
              const first=nextFiles[0]||null;

              setLocalFiles(nextFiles);
              setSourceFile(first);

              if(first){
                setCloudinaryUrl("");
                setCloudinaryPublicId("");
                setCloudinaryWidth(0);
                setCloudinaryHeight(0);
                setCloudinaryViews([]);
              }

              clearResult(
                first
                  ?accurateMode
                    ?`${nextFiles.length}/6 LOCAL VIEWS LOADED`
                    :"LOCAL IMAGE LOADED"
                  :"READY"
              );
              setPipeline("ready");
            }}
          />
          <span className="plus">{hasSource?"✓":"+"}</span>
          <strong>
            {localFiles.length
              ?accurateMode
                ?`${localFiles.length} LOCAL VIEWS SELECTED`
                :localFiles[0]?.name
              :cloudinaryUrl
                ?"CLOUDINARY IMAGE"
                :(accurateMode?"SELECT UP TO 6 LOCAL PHOTOS":"DROP LOCAL IMAGE")}
          </strong>
          <small>
            {accurateMode
              ?"MULTI-SELECT ENABLED · UP TO 6 IMAGES · MAX 8MB EACH"
              :"CLOUDINARY PREFERRED · LOCAL FALLBACK · MAX 8MB"}
          </small>
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
          <span>{full3D?(outputFormat==="stl"?"STL · NO COLOR":"TEXTURED GLB"):`${resolution} × ${resolution}`}</span>
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
              ?"DIRECT PHOTO → 360° TEXTURED MODEL"
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
          <button
            className={outputFormat==="stl"?"active":""}
            onClick={()=>{
              setOutputFormat("stl");
              if(full3D){
                setMessage("FULL 3D STL · NO COLOR SELECTED");
              }else{
                clearResult();
              }
            }}
          >
            {full3D?"STL · NO COLOR":"STL"}
          </button>
          <button
            className={outputFormat==="glb"?"active":""}
            onClick={()=>{
              setOutputFormat("glb");
              if(full3D){
                setMessage("FULL 3D GLB · COLOR SELECTED");
              }else{
                clearResult();
              }
            }}
          >
            {full3D?"GLB · COLOR":"GLB"}
          </button>
        </div>

        {full3D&&<>
          <label className="fieldLabel">GENERATION MODE</label>
          <div className="formats">
            <button
              className={generationMode==="fast"?"active":""}
              onClick={()=>{
                setGenerationMode("fast");
                clearResult("FAST MODE SELECTED");
              }}
            >
              FAST
            </button>
            <button
              className={generationMode==="standard"?"active":""}
              onClick={()=>{
                setGenerationMode("standard");
                clearResult("STANDARD MODE SELECTED");
              }}
            >
              STANDARD
            </button>
          </div>

          <div className="dimension">
            <span>FULL 3D MODE</span>
            <strong>
              {generationMode==="fast"
                ?"FAST · DRAFT · QUICKER · GLB + STL"
                :"STANDARD · HIGHER FIDELITY · GLB + STL"}
            </strong>
          </div>
        </>}

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

        {!full3D&&downloadUrl&&<a className="resultLink" href={downloadUrl}>
          DOWNLOAD {outputFormat.toUpperCase()} ↓
        </a>}

        {full3D&&full3DJobId&&<a
          className="resultLink"
          href={
            outputFormat==="stl"
              ?`${API_BASE}/api/v1/jobs/${full3DJobId}/download-stl`
              :(downloadUrl||`${API_BASE}/api/v1/jobs/${full3DJobId}/download`)
          }
        >
          {outputFormat==="stl"
            ?"DOWNLOAD FULL 3D STL · NO COLOR ↓"
            :"DOWNLOAD TEXTURED GLB · COLOR ↓"}
        </a>}

        {full3D&&full3DJobId&&<a
          className="resultLink"
          href={
            outputFormat==="stl"
              ?(downloadUrl||`${API_BASE}/api/v1/jobs/${full3DJobId}/download`)
              :`${API_BASE}/api/v1/jobs/${full3DJobId}/download-stl`
          }
        >
          {outputFormat==="stl"
            ?"ALSO DOWNLOAD GLB · COLOR ↓"
            :"ALSO DOWNLOAD STL · NO COLOR ↓"}
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
