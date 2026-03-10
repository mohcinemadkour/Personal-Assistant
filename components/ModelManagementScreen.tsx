import React, { useState, useEffect } from 'react';
import { Button } from './Button';
import { LocalModel, ModelStatus } from '../types';
import { MOCK_MODELS } from '../constants';

const StatusIndicator: React.FC<{ status: ModelStatus }> = ({ status }) => {
    const statusInfo = {
        [ModelStatus.Running]: { color: 'bg-green-500', text: 'Running' },
        [ModelStatus.Idle]: { color: 'bg-yellow-500', text: 'Idle' },
        [ModelStatus.NotDownloaded]: { color: 'bg-gray-400', text: 'Not Downloaded' },
    };
    const currentStatus = statusInfo[status];

    return (
        <div className="flex items-center space-x-2">
            <span className={`h-2.5 w-2.5 rounded-full ${currentStatus.color}`}></span>
            <span className="text-sm text-gray-500">{currentStatus.text}</span>
        </div>
    );
};

export const ModelManagementScreen: React.FC = () => {
    const [models, setModels] = useState<LocalModel[]>([]);
    const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
    const [serverUp, setServerUp] = useState(false);
    const [configuredModel, setConfiguredModel] = useState<string | null>(null);
    const [loadingModel, setLoadingModel] = useState<string | null>(null);

    const fetchModels = async () => {
        try {
            const [mResp, sResp] = await Promise.all([
                fetch('/api/models'), 
                fetch('/api/openai/status')
            ]);
            
            let openaiModels: any[] = [];
            let configured = null;

            if (sResp.ok) {
                const sd = await sResp.json();
                setApiKeyConfigured(!!sd.cli_available);
                setServerUp(!!sd.server_up);
            }

            if (mResp.ok) {
                const md = await mResp.json();
                openaiModels = md.models || [];
                configured = md.configured || null;
                setConfiguredModel(configured);
            }

            // Map OpenAI models to LocalModel format
            const allModels: LocalModel[] = openaiModels.map((m: any, idx: number) => {
                const isActive = m.name === configured;
                return {
                    id: `openai-${idx}`,
                    name: m.name,
                    size: m.size,
                    status: ModelStatus.Running,  // OpenAI models are always "available"
                    isActive: isActive
                };
            });

            setModels(allModels);
        } catch (e) {
            console.error("Failed to fetch models", e);
        }
    };

    useEffect(() => { 
        fetchModels(); 
        const interval = setInterval(fetchModels, 5000);
        return () => clearInterval(interval);
    }, []);

    const handlePull = async (name: string) => {
        // OpenAI models don't need to be "pulled"
        alert('OpenAI models are managed via API. No download needed!');
    };

    const handleRemove = async (name: string) => {
        // OpenAI models can't be removed
        alert('OpenAI models cannot be removed. They are managed via API.');
    };

    const handleActivate = async (name: string) => {
        setLoadingModel(name);
        try {
            const resp = await fetch('/api/models/activate', { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify({ model: name }) 
            });
            const data = await resp.json();
            if (!data.ok) throw new Error(data.error || 'Failed to activate model');
            fetchModels();
        } catch (e) {
            alert('Error activating model: ' + (e as Error).message);
        } finally { setLoadingModel(null); }
    };
    return (
        <div className="p-10 max-w-4xl mx-auto">
            <div className="flex justify-between items-start mb-1">
                <h2 className="text-3xl font-bold text-gray-900">Model Management</h2>
                <Button variant="ghost" onClick={fetchModels} disabled={!!loadingModel}>Refresh</Button>
            </div>
            <p className="text-gray-500 mb-8">Select an OpenAI model for generating your summaries. All models are cloud-hosted and always available.</p>

            {!apiKeyConfigured && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                    <strong>OpenAI API Key not configured.</strong> Please set the OPENAI_API_KEY environment variable.
                </div>
            )}

            {apiKeyConfigured && !serverUp && (
                <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-xl text-yellow-700 text-sm">
                    <strong>Cannot reach OpenAI API.</strong> Please check your internet connection and API key.
                </div>
            )}

            {apiKeyConfigured && serverUp && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-xl text-green-700 text-sm">
                    <strong>✓ OpenAI API Connected.</strong> All models are ready to use.
                </div>
            )}

            <div className="space-y-4">
                {models.map(model => (
                    <div key={model.id} className={`flex items-center justify-between p-4 rounded-xl border shadow-sm transition-all ${model.isActive ? 'bg-blue-50 border-blue-200 ring-1 ring-blue-100' : 'bg-white border-gray-200'}`}>
                        <div className="flex-1">
                            <div className="flex items-center space-x-2">
                                <h3 className="font-semibold text-gray-800">{model.name}</h3>
                                {model.isActive && (
                                    <span className="text-[10px] font-bold bg-blue-600 text-white px-1.5 py-0.5 rounded uppercase tracking-wider">Active</span>
                                )}
                            </div>
                            <div className="flex items-center space-x-4">
                                <p className="text-sm text-gray-500">{model.size}</p>
                                <div className="flex items-center space-x-2">
                                    <span className={`h-2.5 w-2.5 rounded-full bg-green-500`}></span>
                                    <span className="text-sm text-gray-500">Available</span>
                                </div>
                            </div>
                        </div>
                        <div className="flex items-center space-x-3">
                            {model.isActive ? (
                                <span className="text-sm text-blue-600 font-semibold">Currently Selected</span>
                            ) : (
                                <Button 
                                    variant="primary" 
                                    onClick={() => handleActivate(model.name)} 
                                    disabled={!!loadingModel}
                                    className="text-sm"
                                >
                                    {loadingModel === model.name ? 'Setting...' : 'Select'}
                                </Button>
                            )}
                        </div>
                    </div>
                ))}
            </div>
            <p className="text-center text-xs text-gray-500 mt-6">Note: All OpenAI models are cloud-hosted and managed via API. No local installation required.</p>
        </div>
    );
};