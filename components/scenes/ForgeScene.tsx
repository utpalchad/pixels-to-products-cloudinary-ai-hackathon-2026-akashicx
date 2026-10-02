"use client";
import {Canvas,useFrame} from "@react-three/fiber";
import {Environment,Float,OrbitControls} from "@react-three/drei";
import {useRef} from "react";
import * as THREE from "three";

function Form(){
  const group=useRef<THREE.Group>(null);

  useFrame((s,d)=>{
    if(!group.current) return;

    group.current.rotation.y+=Math.min(d,.04)*.055;
    group.current.rotation.x=THREE.MathUtils.lerp(
      group.current.rotation.x,
      s.pointer.y*.1,
      .028
    );
    group.current.rotation.z=THREE.MathUtils.lerp(
      group.current.rotation.z,
      -s.pointer.x*.045,
      .025
    );
  });

  return <group ref={group}>
    <Float speed={.95} rotationIntensity={.12} floatIntensity={.24}>
      <mesh rotation={[.16,.12,0]}>
        <torusKnotGeometry args={[1.44,.43,120,20,2,3]}/>
        <meshStandardMaterial
          color="#d9d5ff"
          roughness={.2}
          metalness={.62}
          envMapIntensity={1.25}
        />
      </mesh>

      <mesh scale={1.018} rotation={[.16,.12,0]}>
        <torusKnotGeometry args={[1.44,.43,54,10,2,3]}/>
        <meshBasicMaterial
          color="#57e6ff"
          wireframe
          transparent
          opacity={.13}
        />
      </mesh>

      <mesh scale={.54} rotation={[-.22,.35,.4]}>
        <icosahedronGeometry args={[1.08,2]}/>
        <meshStandardMaterial
          color="#7c3cff"
          roughness={.24}
          metalness={.7}
          transparent
          opacity={.76}
        />
      </mesh>
    </Float>
  </group>
}

export default function ForgeScene(){
  return <Canvas
    camera={{position:[0,0,5.9],fov:40}}
    dpr={[1,1.25]}
    gl={{
      alpha:true,
      antialias:false,
      powerPreference:"high-performance"
    }}
    performance={{min:.55}}
  >
    <ambientLight intensity={.62}/>
    <directionalLight position={[3.5,4.5,4]} intensity={2.2} color="#ffffff"/>
    <pointLight position={[-3,1.5,3]} intensity={21} distance={8} color="#ff2d2d"/>
    <pointLight position={[3,-.5,2.5]} intensity={23} distance={8} color="#57e6ff"/>
    <pointLight position={[0,3,-1]} intensity={17} distance={7} color="#ffd400"/>
    <Form/>
    <Environment preset="studio"/>
    <OrbitControls
      enablePan={false}
      enableZoom={false}
      autoRotate
      autoRotateSpeed={.16}
      enableDamping
      dampingFactor={.07}
    />
  </Canvas>
}
