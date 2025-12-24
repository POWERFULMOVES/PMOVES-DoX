'use client';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  MessageSquare, 
  Database, 
  BrainCircuit, 
  Network, 
  Activity, 
  Zap, 
  Cpu, 
  ShieldCheck, 
  AlertTriangle,
  Search,
  Settings as SettingsIcon
} from 'lucide-react';

import FileUpload from '@/components/FileUpload';
import QAInterface from '@/components/QAInterface';
import FactsViewer from '@/components/FactsViewer';
import CHRPanel from '@/components/CHRPanel';
import LogsPanel from '@/components/LogsPanel';
import APIsPanel from '@/components/APIsPanel';
import TagsPanel from '@/components/TagsPanel';
import ArtifactsPanel from '@/components/ArtifactsPanel';
import EntitiesPanel from '@/components/EntitiesPanel';
import StructurePanel from '@/components/StructurePanel';
import MetricHitsPanel from '@/components/MetricHitsPanel';
import SummariesPanel from '@/components/SummariesPanel';
import MediaArtifactsPanel from '@/components/MediaArtifactsPanel';
import GlobalSearch from '@/components/GlobalSearch';
import SettingsModal from '@/components/SettingsModal';

import MemoryViewer from '@/components/MemoryViewer';
import SkillsRegistry from '@/components/SkillsRegistry';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { getApiBase, getHRMEnabled } from '@/lib/config';
import A2UIRenderer from '@/components/a2ui/A2UIRenderer';
import { api } from '@/lib/api';

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [vlmRepo, setVlmRepo] = useState<string | null>(null);
  const [queuedCount, setQueuedCount] = useState<number>(0);
  const [activeTab, setActiveTab] = useState('workspace');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [hrmEnabled, setHrmEnabled] = useState(false);
  const [a2uiContent, setA2uiContent] = useState<any[]>([]);

  useEffect(() => {
    if (activeTab === 'a2ui') {
        api.getA2UIDemo().then(setA2uiContent).catch(console.error);
    }
  }, [activeTab]);

  const saveBlueprint = async () => {
      if (a2uiContent.length === 0) return;
      try {
          await api.addMemory('blueprint', a2uiContent);
          alert('Blueprint saved to Cipher Memory!');
      } catch (e) {
          console.error(e);
          alert('Failed to save blueprint.');
      }
  };
  
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const API = getApiBase();
    setHrmEnabled(getHRMEnabled());
    
    // Initial config fetch
    fetch(`${API}/config`).then(async (r) => {
      if (!r.ok) return;
      const cfg = await r.json();
      if (cfg?.vlm_repo) setVlmRepo(cfg.vlm_repo as string);
    }).catch(() => {});

    // Poll tasks summary
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/tasks`);
        if (!r.ok) return;
        const t = await r.json();
        setQueuedCount(Number(t?.queued || 0));
      } catch {}
    }, 5000);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleUploadComplete = () => {
    setRefreshKey(prev => prev + 1);
  };

  const tabs = [
    { id: 'workspace', label: 'Workspace', icon: Database },
    { id: 'modellab', label: 'Model Lab', icon: BrainCircuit },
    { id: 'knowledge', label: 'Knowledge Graph', icon: Network },
    { id: 'a2ui', label: 'A2UI Lab', icon: Cpu },
    { id: 'system', label: 'System', icon: Activity },
  ];

  return (
    <div className="space-y-8 pb-12">
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />

      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
            Mission Control
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage documents, analyze reasoning, and monitor system health.
          </p>
        </div>
        
        <div className="flex items-center gap-3">
           <div className="w-64 hidden md:block">
              <GlobalSearch />
           </div>
           
           <button 
             onClick={() => setSettingsOpen(true)}
             className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-colors"
           >
              <SettingsIcon size={20} className="text-muted-foreground" />
           </button>

           {vlmRepo && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium">
              <Zap size={14} />
              <span className="hidden lg:inline">VLM: {vlmRepo}</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 p-1 bg-white/5 border border-white/5 rounded-xl w-fit overflow-x-auto max-w-full">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap",
                isActive 
                  ? "bg-primary text-white shadow-lg shadow-primary/20" 
                  : "text-muted-foreground hover:text-white hover:bg-white/5"
              )}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'workspace' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <div className="lg:col-span-4 space-y-6">
                  <Card className="glass-card border-white/5">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                         <Upload className="text-primary" size={20}/> Ingest
                      </CardTitle>
                      <CardDescription>Upload documents for processing</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <FileUpload onUploadComplete={handleUploadComplete} />
                    </CardContent>
                  </Card>
                </div>
                <div className="lg:col-span-8">
                   <Card className="glass-card border-white/5 h-full">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <MessageSquare className="text-cyan-400" size={20}/> Analysis
                      </CardTitle>
                      <CardDescription>Interactive QA with citations</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <QAInterface />
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <Card className="glass-card border-white/5">
                    <CardHeader>
                      <CardTitle>Extracted Facts</CardTitle>
                    </CardHeader>
                    <CardContent>
                       <FactsViewer key={refreshKey} />
                    </CardContent>
                 </Card>
                 <Card className="glass-card border-white/5">
                    <CardHeader>
                      <CardTitle>Reasoning Chains</CardTitle>
                    </CardHeader>
                    <CardContent>
                       <CHRPanel />
                    </CardContent>
                 </Card>
              </div>

               <div className="grid grid-cols-1 gap-6">
                 <Card className="glass-card border-white/5">
                    <CardHeader>
                       <CardTitle>Artifacts & Summaries</CardTitle>
                    </CardHeader>
                    <CardContent className="grid md:grid-cols-2 gap-6">
                       <ArtifactsPanel />
                       <SummariesPanel />
                    </CardContent>
                 </Card>
              </div>

              {/* New row for MemoryViewer and SkillsRegistry */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <Card className="glass-card border-white/5">
                  <CardHeader>
                    <CardTitle>Memory Viewer</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <MemoryViewer />
                  </CardContent>
                </Card>
                <Card className="glass-card border-white/5">
                  <CardHeader>
                    <CardTitle>Skills Registry</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <SkillsRegistry />
                  </CardContent>
                </Card>
                {/* Placeholder for a third item if needed, or adjust grid to 2 columns */}
                <Card className="glass-card border-white/5 flex items-center justify-center">
                  <CardContent className="text-muted-foreground/50 text-sm">
                    Additional Workspace Item
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {activeTab === 'modellab' && (
             <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                   <Card className="glass-card border-white/5 bg-gradient-to-br from-purple-500/10 to-transparent">
                      <CardHeader>
                         <CardTitle className="flex items-center gap-2">
                            <BrainCircuit size={20} className="text-purple-400"/> Sidecar Status
                         </CardTitle>
                      </CardHeader>
                      <CardContent>
                         <div className="space-y-4">
                            <div className="flex justify-between items-center text-sm">
                               <span className="text-muted-foreground">Model</span>
                               <span className="font-mono text-white">SmolLM2-360M</span>
                            </div>
                            <div className="flex justify-between items-center text-sm">
                               <span className="text-muted-foreground">Sidecar Confidence</span>
                               <span className="text-green-400 font-bold">98.2%</span>
                            </div>
                            <div className="h-2 bg-black/20 rounded-full overflow-hidden">
                               <div className="h-full bg-purple-500 w-[98%]" />
                            </div>
                         </div>
                      </CardContent>
                   </Card>

                    <Card className="glass-card border-white/5">
                      <CardHeader>
                         <CardTitle className="flex items-center gap-2">
                            <ShieldCheck size={20} className="text-green-400"/> Adversarial Mining
                         </CardTitle>
                      </CardHeader>
                      <CardContent>
                         <div className="text-center py-6 text-muted-foreground text-sm">
                            <AlertTriangle className="mx-auto mb-2 opacity-50" size={32}/>
                            No adversarial samples detected in last run.
                         </div>
                      </CardContent>
                   </Card>

                   <Card className="glass-card border-white/5">
                      <CardHeader>
                         <CardTitle className="flex items-center gap-2">
                            <Zap size={20} className="text-yellow-400"/> HRM Metrics
                         </CardTitle>
                      </CardHeader>
                      <CardContent>
                          <div className="space-y-2">
                             <div className="flex justify-between text-sm">
                                <span>Avg Steps</span>
                                <span className="font-mono">2.4</span>
                             </div>
                             <div className="flex justify-between text-sm">
                                <span>Mmax Cap</span>
                                <span className="font-mono">6</span>
                             </div>
                             <div className="flex justify-between text-sm">
                                <span>Halting Policy</span>
                                <span className="text-cyan-400 font-mono">ACT-Active</span>
                             </div>
                          </div>
                      </CardContent>
                   </Card>
                </div>

                <Card className="glass-card border-white/5">
                   <CardHeader>
                      <CardTitle>Latent Refinement Trace (Mock)</CardTitle>
                      <CardDescription>Visualizing the HRM step-by-step reasoning refinement.</CardDescription>
                   </CardHeader>
                   <CardContent>
                      <div className="space-y-4 p-4 bg-black/20 rounded-lg font-mono text-sm">
                         <div className="flex gap-4 border-l-2 border-purple-500 pl-4">
                            <div className="text-purple-400 font-bold">Step 1</div>
                            <div className="text-white/60">"The user is asking about sidecar GANs."</div>
                         </div>
                         <div className="flex gap-4 border-l-2 border-purple-500 pl-4 py-2 bg-purple-500/5">
                            <div className="text-purple-400 font-bold">Step 2</div>
                            <div className="text-white/80">"Critique: Specifically mentioned documentation. Need to verify context."</div>
                         </div>
                         <div className="flex gap-4 border-l-2 border-green-500 pl-4">
                            <div className="text-green-400 font-bold">Final</div>
                            <div className="text-white">"Found 3 relevant documents. Halting."</div>
                         </div>
                      </div>
                   </CardContent>
                </Card>
             </div>
          )}

          {activeTab === 'knowledge' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
               <EntitiesPanel refreshKey={refreshKey} />
               <StructurePanel refreshKey={refreshKey} />
               <MetricHitsPanel refreshKey={refreshKey} />
               <MediaArtifactsPanel />
               <MediaArtifactsPanel />
            </div>
          )}

          {activeTab === 'a2ui' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card className="glass-card border-white/5">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                           <Cpu className="text-purple-400" /> A2UI Renderer (React)
                        </CardTitle>
                        <CardDescription>
                            Rendering Agent-to-UI JSON payloads natively in React.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <A2UIRenderer content={a2uiContent} />
                        <div className="mt-6 flex justify-end">
                            <button 
                                onClick={saveBlueprint}
                                className="px-4 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-md text-sm font-medium transition-colors border border-primary/20"
                            >
                                Save as Cipher Blueprint
                            </button>
                        </div>
                    </CardContent>
                </Card>

                <Card className="glass-card border-white/5">
                    <CardHeader>
                        <CardTitle>Protocol Stream</CardTitle>
                        <CardDescription>Live JSONL Stream from Agent</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <pre className="bg-black/40 p-4 rounded-lg text-xs font-mono text-green-400/80 overflow-auto max-h-[500px]">
                            {JSON.stringify(a2uiContent, null, 2)}
                        </pre>
                    </CardContent>
                </Card>
              </div>
          )}

          {activeTab === 'system' && (
             <div className="space-y-6">
                <LogsPanel />
                <APIsPanel />
                <TagsPanel />
             </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
