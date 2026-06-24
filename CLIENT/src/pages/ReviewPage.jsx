import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './ReviewPage.css';
import { API_BASE } from '../utils/api';

// ---- Skill Keywords for Autocomplete ----
const SKILL_KEYWORDS = {
  "Web Technologies": ["React", "Node", "Angular", "Vue", "Django", "Flask", "Spring Boot", "HTML", "CSS", "Tailwind", "Bootstrap", "Next.js", "Express", "Streamlit", "MERN"],
  "Languages": ["Python", "Java", "C++", "C#", "SQL", "JavaScript", "TypeScript", "Kotlin", "Swift", "Ruby", "PHP", "Go", "C"],
  "Operating System": ["Linux", "Windows", "Ubuntu", "Unix", "MacOS", "Android", "iOS"],
  "Tools": ["Git", "GitHub", "Docker", "Kubernetes", "Jenkins", "Jira", "Postman", "Excel", "PowerBI", "Tableau", "VS Code", "Figma", "Canva"],
  "Technologies": ["Machine Learning", "Deep Learning", "NLP", "Data Science", "AWS", "Azure", "Google Cloud", "GCP", "Blockchain", "IoT", "Big Data", "TensorFlow", "Keras", "OpenCV", "Generative AI", "Artificial Intelligence"],
};

const ALL_SKILLS = [];
Object.entries(SKILL_KEYWORDS).forEach(([cat, skills]) => {
  skills.forEach((s) => ALL_SKILLS.push({ name: s, category: cat }));
});

// ---- Skill Autocomplete Component ----
function SkillAutocomplete({ existingSkills, onAdd, placeholder = "+ Add skill" }) {
  const [query, setQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const wrapperRef = useRef(null);

  const existingLower = existingSkills.map((s) => s.toLowerCase());
  const suggestions = query.trim()
    ? ALL_SKILLS.filter(
        (s) =>
          s.name.toLowerCase().includes(query.toLowerCase()) &&
          !existingLower.includes(s.name.toLowerCase())
      ).slice(0, 8)
    : [];

  const exactMatch = suggestions.some((s) => s.name.toLowerCase() === query.trim().toLowerCase());
  const showCustom = query.trim().length > 0 && !exactMatch && !existingLower.includes(query.trim().toLowerCase());

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (skillName) => {
    onAdd(skillName);
    setQuery('');
    setShowDropdown(false);
    setActiveIdx(-1);
  };

  const handleKeyDown = (e) => {
    const totalItems = suggestions.length + (showCustom ? 1 : 0);
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((prev) => (prev < totalItems - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((prev) => (prev > 0 ? prev - 1 : totalItems - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeIdx >= 0 && activeIdx < suggestions.length) {
        handleSelect(suggestions[activeIdx].name);
      } else if (activeIdx === suggestions.length && showCustom) {
        handleSelect(query.trim());
      } else if (query.trim() && suggestions.length > 0) {
        handleSelect(suggestions[0].name);
      } else if (query.trim()) {
        handleSelect(query.trim());
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  return (
    <div className="skill-autocomplete-wrapper" ref={wrapperRef}>
      <input
        className="skill-add-input"
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setShowDropdown(true);
          setActiveIdx(-1);
        }}
        onFocus={() => setShowDropdown(true)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
      />
      {showDropdown && (suggestions.length > 0 || showCustom) && (
        <div className="skill-suggestions">
          {suggestions.map((s, idx) => (
            <div
              key={s.name}
              className={`skill-suggestion-item ${idx === activeIdx ? 'active' : ''}`}
              onClick={() => handleSelect(s.name)}
              onMouseEnter={() => setActiveIdx(idx)}
            >
              <span>{s.name}</span>
              <span className="suggestion-category">{s.category}</span>
            </div>
          ))}
          {showCustom && (
            <div
              className={`skill-add-custom ${activeIdx === suggestions.length ? 'active' : ''}`}
              onClick={() => handleSelect(query.trim())}
              onMouseEnter={() => setActiveIdx(suggestions.length)}
            >
              + Add "{query.trim()}"
            </div>
          )}
        </div>
      )}
    </div>
  );
}


function ReviewPage({ extractedData, onGenerateComplete }) {
  const navigate = useNavigate();
  const [data, setData] = useState(extractedData);
  const [openSections, setOpenSections] = useState({
    basic: true,
    experience: true,
    skills: false,
    achievements: false,
    education: false,
  });
  const [generating, setGenerating] = useState(false);

  const toggleSection = (key) => setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));

  const updateField = (path, value) => {
    setData((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      const keys = path.split('.');
      let obj = next;
      for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]];
      obj[keys[keys.length - 1]] = value;
      return next;
    });
  };

  const updateExperience = (expIdx, field, value) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences[expIdx][field] = value;
    return next;
  });

  const updateProject = (expIdx, projIdx, field, value) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences[expIdx].projects[projIdx][field] = value;
    return next;
  });

  const addExperience = () => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences.push({ company: '', designation: '', duration: '', location: '', projects: [{ client: '', project_name: '', project_span: '', technologies: [], description: '', role_responsibility: '' }] });
    return next;
  });

  const removeExperience = (expIdx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences.splice(expIdx, 1);
    return next;
  });

  const addProject = (expIdx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences[expIdx].projects.push({ client: '', project_name: '', project_span: '', technologies: [], description: '', role_responsibility: '' });
    return next;
  });

  const removeProject = (expIdx, projIdx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences[expIdx].projects.splice(projIdx, 1);
    return next;
  });

  const addTech = (expIdx, projIdx, tech) => {
    if (!tech.trim()) return;
    setData((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      next.Experience.experiences[expIdx].projects[projIdx].technologies.push(tech.trim());
      return next;
    });
  };

  const removeTech = (expIdx, projIdx, techIdx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Experience.experiences[expIdx].projects[projIdx].technologies.splice(techIdx, 1);
    return next;
  });

  const addSkill = (category, skill) => {
    if (!skill.trim()) return;
    setData((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (!next.Skills[category]) next.Skills[category] = [];
      if (!next.Skills[category].map(s => s.toLowerCase()).includes(skill.trim().toLowerCase())) {
        next.Skills[category].push(skill.trim());
      }
      return next;
    });
  };

  const removeSkill = (category, idx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Skills[category].splice(idx, 1);
    if (next.Skills[category].length === 0) delete next.Skills[category];
    return next;
  });

  const addSkillCategory = (catName) => {
    if (!catName.trim()) return;
    setData((prev) => {
      const next = JSON.parse(JSON.stringify(prev));
      if (!next.Skills[catName.trim()]) next.Skills[catName.trim()] = [];
      return next;
    });
  };

  const updateAchievement = (idx, value) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Achievements[idx] = value;
    return next;
  });

  const addAchievement = () => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Achievements.push('');
    return next;
  });

  const removeAchievement = (idx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Achievements.splice(idx, 1);
    return next;
  });

  const updateEducation = (idx, field, value) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Education[idx][field] = value;
    return next;
  });

  const addEducation = () => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Education.push({ college: '', degree: '', graduation_year: '', grade: '' });
    return next;
  });

  const removeEducation = (idx) => setData((prev) => {
    const next = JSON.parse(JSON.stringify(prev));
    next.Education.splice(idx, 1);
    return next;
  });

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const response = await fetch(`${API_BASE}/generate-resume`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error('Failed to generate resume');
      const blob = await response.blob();
      const contentDisposition = response.headers.get('Content-Disposition');
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1].replace(/"/g, '')
        : 'resume_ncircle.pdf';
      console.log('Blob:', blob);
      console.log('Filename:', filename);
      console.log('Timestamp:', new Date().toISOString());
      onGenerateComplete({ blob, filename, timestamp: new Date().toISOString() });
      navigate('/download');
    } catch (error) {
      console.error('Error generating resume:', error);
      alert('Error generating resume. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleTagKeyDown = (e, addFn) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addFn(e.target.value);
      e.target.value = '';
    }
  };

  const ChevronDown = () => (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6l4 4 4-4" />
    </svg>
  );

  const allExistingSkills = Object.values(data.Skills || {}).flat();

  if (!data) return null;

  return (
    <div className="review-page glass-card">
      <div className="review-header">
        <div>
          <h1 className="review-heading">Review your details</h1>
          <p className="review-subtitle">Edit or fill in missing fields, then generate your formal resume.</p>
        </div>
        <div className="generate-area">
          <button
            className={`primary-btn generate-button ${generating ? 'loading' : ''}`}
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? 'Generating...' : 'Generate nCircle Resume'}
          </button>
        </div>  
      </div>

      <div className="review-sections">
        {/* ===================== BASIC DETAILS ===================== */}
        <div className="review-section">
          <div className="section-header" onClick={() => toggleSection('basic')}>
            <div className="section-header-left">
              {/* <span className="section-icon">👤</span> */}
              <span className="section-title">Basic Details</span>
            </div>
            <span className={`section-toggle ${openSections.basic ? 'open' : ''}`}><ChevronDown /></span>
          </div>
          {openSections.basic && (
            <div className="section-body">
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input className="form-input" type="text" value={data.Name || ''} onChange={(e) => updateField('Name', e.target.value)} placeholder="Enter full name" />
                </div>
                <div className="form-group">
                  <label className="form-label">Total Experience (Years)</label>
                  <input className="form-input" type="number" step="0.5" value={data.Experience?.total_experience_years ?? ''} onChange={(e) => updateField('Experience.total_experience_years', parseFloat(e.target.value) || 0)} placeholder="e.g. 2.5" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ===================== EXPERIENCE ===================== */}
        <div className="review-section">
          <div className="section-header" onClick={() => toggleSection('experience')}>
            <div className="section-header-left">
              {/* <span className="section-icon">💼</span> */}
              <span className="section-title">Experience</span>
            </div>
            <span className={`section-toggle ${openSections.experience ? 'open' : ''}`}><ChevronDown /></span>
          </div>
          {openSections.experience && (
            <div className="section-body">
              {(data.Experience?.experiences || []).map((exp, expIdx) => (
                <div className="entry-block" key={expIdx}>
                  <div className="entry-block-header">
                    <span className="entry-block-title">{exp.company || `Experience #${expIdx + 1}`}</span>
                    <button className="entry-remove-btn" onClick={() => removeExperience(expIdx)}>✕ Remove</button>
                  </div>
                  <div className="form-row four-col">
                    <div className="form-group">
                      <label className="form-label">Company</label>
                      <input className="form-input" type="text" value={exp.company || ''} onChange={(e) => updateExperience(expIdx, 'company', e.target.value)} placeholder="Company name" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Designation</label>
                      <input className="form-input" type="text" value={exp.designation || ''} onChange={(e) => updateExperience(expIdx, 'designation', e.target.value)} placeholder="e.g. SDE" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Duration</label>
                      <input className="form-input" type="text" value={exp.duration || ''} onChange={(e) => updateExperience(expIdx, 'duration', e.target.value)} placeholder="Jan 2022 – Present" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Location</label>
                      <input className="form-input" type="text" value={exp.location || ''} onChange={(e) => updateExperience(expIdx, 'location', e.target.value)} placeholder="City, Country" />
                    </div>
                  </div>

                  {(exp.projects || []).map((proj, projIdx) => (
                    <div className="project-block" key={projIdx}>
                      <div className="project-block-header">
                        <span className="project-block-title">{proj.project_name || `Project #${projIdx + 1}`}</span>
                        {exp.projects.length > 1 && (
                          <button className="entry-remove-btn" onClick={() => removeProject(expIdx, projIdx)}>✕</button>
                        )}
                      </div>
                      <div className="form-row three-col">
                        <div className="form-group">
                          <label className="form-label">Client</label>
                          <input className="form-input" type="text" value={proj.client || ''} onChange={(e) => updateProject(expIdx, projIdx, 'client', e.target.value)} placeholder="Client name" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">Project Name</label>
                          <input className="form-input" type="text" value={proj.project_name || ''} onChange={(e) => updateProject(expIdx, projIdx, 'project_name', e.target.value)} placeholder="Project name" />
                        </div>
                        <div className="form-group">
                          <label className="form-label">Project Span</label>
                          <input className="form-input" type="text" value={proj.project_span || ''} onChange={(e) => updateProject(expIdx, projIdx, 'project_span', e.target.value)} placeholder="e.g. 6 months" />
                        </div>
                      </div>
                      <div className="form-group" style={{ marginBottom: '0.5rem' }}>
                        <label className="form-label">Technologies</label>
                        <div className="project-tech-tags">
                          {(proj.technologies || []).map((tech, tIdx) => (
                            <span className="tech-tag" key={tIdx}>
                              {tech}
                              <button className="tech-remove" onClick={() => removeTech(expIdx, projIdx, tIdx)}>✕</button>
                            </span>
                          ))}
                          <input className="tech-add-input" style={{width: '200px'}} type="text" placeholder="+ Add tech and press Enter" onKeyDown={(e) => handleTagKeyDown(e, (val) => addTech(expIdx, projIdx, val))} />
                        </div>
                      </div>
                      <div className="form-row">
                        <div className="form-group">
                          <label className="form-label">Description</label>
                          <textarea className="form-textarea" value={proj.description || ''} onChange={(e) => updateProject(expIdx, projIdx, 'description', e.target.value)} placeholder="Describe the project..." />
                        </div>
                        <div className="form-group">
                          <label className="form-label">Role / Responsibility</label>
                          <textarea className="form-textarea" value={proj.role_responsibility || ''} onChange={(e) => updateProject(expIdx, projIdx, 'role_responsibility', e.target.value)} placeholder="Your role..." />
                        </div>
                      </div>
                    </div>
                  ))}
                  <button className="add-item-btn" onClick={() => addProject(expIdx)}>＋ Add Project</button>
                </div>
              ))}
              <button className="add-item-btn" onClick={addExperience}>＋ Add Experience</button>
            </div>
          )}
        </div>

        {/* ===================== EDUCATION ===================== */}
        <div className="review-section">
          <div className="section-header" onClick={() => toggleSection('education')}>
            <div className="section-header-left">
              {/* <span className="section-icon">🎓</span> */}
              <span className="section-title">Education</span>
            </div>
            <span className={`section-toggle ${openSections.education ? 'open' : ''}`}><ChevronDown /></span>
          </div>
          {openSections.education && (
            <div className="section-body">
              {(data.Education || []).map((edu, idx) => (
                <div className="entry-block" key={idx}>
                  <div className="entry-block-header">
                    <span className="entry-block-title">Institution #{idx + 1}</span>
                    {data.Education.length > 1 && (
                      <button className="entry-remove-btn" onClick={() => removeEducation(idx)}>✕ Remove</button>
                    )}
                  </div>
                  <div className="form-row four-col">
                    <div className="form-group">
                      <label className="form-label">College</label>
                      <input className="form-input" type="text" value={edu.college || ''} onChange={(e) => updateEducation(idx, 'college', e.target.value)} placeholder="Institution name" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Degree</label>
                      <input className="form-input" type="text" value={edu.degree || ''} onChange={(e) => updateEducation(idx, 'degree', e.target.value)} placeholder="e.g. B.Tech in CS" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Graduation Year</label>
                      <input className="form-input" type="text" value={edu.graduation_year || ''} onChange={(e) => updateEducation(idx, 'graduation_year', e.target.value)} placeholder="e.g. 2024" />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Grade</label>
                      <input className="form-input" type="text" value={edu.grade || ''} onChange={(e) => updateEducation(idx, 'grade', e.target.value)} placeholder="e.g. 9.0" />
                    </div>
                  </div>
                </div>
              ))}
              <button className="add-item-btn" onClick={addEducation}>＋ Add Education</button>
            </div>
          )}
        </div>

        {/* ===================== SKILLS ===================== */}
        <div className="review-section">
          <div className="section-header" onClick={() => toggleSection('skills')}>
            <div className="section-header-left">
              {/* <span className="section-icon">💡</span> */}
              <span className="section-title">Skills</span>
            </div>
            <span className={`section-toggle ${openSections.skills ? 'open' : ''}`}><ChevronDown /></span>
          </div>
          {openSections.skills && (
            <div className="section-body">
              {Object.entries(data.Skills || {}).map(([category, skills]) => (
                <div className="skills-category" key={category}>
                  <div className="skills-category-header">
                    <span className="skills-category-name">{category}</span>
                  </div>
                  <div className="skills-tags">
                    {skills.map((skill, sIdx) => (
                      <span className="skill-tag" key={sIdx}>
                        {skill}
                        <button className="skill-remove" onClick={() => removeSkill(category, sIdx)}>✕</button>
                      </span>
                    ))}
                    <div style={{ width: '200px' }}>
                      <SkillAutocomplete
                        existingSkills={allExistingSkills}
                        onAdd={(val) => addSkill(category, val)}
                      />
                    </div>
                  </div>
                </div>
              ))}
              <button
                className="add-category-btn"
                onClick={() => {
                  const name = prompt('Enter new skill category name:');
                  if (name) addSkillCategory(name);
                }}
              >
                ＋ Add Category
              </button>
            </div>
          )}
        </div>

        {/* ===================== ACHIEVEMENTS ===================== */}
        <div className="review-section">
          <div className="section-header" onClick={() => toggleSection('achievements')}>
            <div className="section-header-left">
              {/* <span className="section-icon">🏆</span> */}
              <span className="section-title">Achievements</span>
            </div>
            <span className={`section-toggle ${openSections.achievements ? 'open' : ''}`}><ChevronDown /></span>
          </div>
          {openSections.achievements && (
            <div className="section-body">
              <div className="achievements-compact">
                {(data.Achievements || []).map((ach, idx) => (
                  <div className="achievement-item" key={idx}>
                    <span className="achievement-number">{idx + 1}</span>
                    <input className="form-input achievement-input" type="text" value={ach} onChange={(e) => updateAchievement(idx, e.target.value)} placeholder="Enter achievement" />
                    <button className="achievement-remove" onClick={() => removeAchievement(idx)}>✕</button>
                  </div>
                ))}
              </div>
              <button className="add-item-btn" onClick={addAchievement}>＋ Add Achievement</button>
            </div>
          )}
        </div>
      </div>

      {/* ===================== GENERATE BUTTON ===================== */}
      
      {generating && (
        <div className="generating-overlay">
          <div className="generating-spinner"></div>
          <p className="generating-text">Generating your resume...</p>
        </div>
      )}
    </div>
  );
}

export default ReviewPage;
