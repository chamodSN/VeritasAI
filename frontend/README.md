# VeritasAI Frontend

A modern React frontend for the VeritasAI Legal Multi-Agent System, built with React 18, Tailwind CSS, and Axios.

## Features

- **Modern React 18** with hooks and functional components
- **Tailwind CSS** for responsive, utility-first styling
- **Axios** for HTTP requests to the VeritasAI API
- **Font Awesome** icons for enhanced UI
- **Responsive Design** that works on all devices
- **Real-time Query Processing** with loading states
- **Error Handling** with user-friendly messages
- **Sample Queries** for quick testing

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- VeritasAI backend server running on `http://localhost:8000`

## Installation

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```

4. **Open your browser** and go to `http://localhost:3000`

## Available Scripts

- `npm start` - Runs the app in development mode
- `npm build` - Builds the app for production
- `npm test` - Launches the test runner
- `npm eject` - Ejects from Create React App (one-way operation)

## Project Structure

```
frontend/
├── public/
│   ├── index.html          # Main HTML template
│   └── manifest.json       # PWA manifest
├── src/
│   ├── App.js             # Main React component
│   ├── index.js           # React entry point
│   └── index.css          # Tailwind CSS imports
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind configuration
└── postcss.config.js      # PostCSS configuration
```

## Configuration

### API Endpoint
The frontend is configured to connect to the VeritasAI API at `http://localhost:8000`. To change this:

1. Edit `src/App.js`
2. Update the `apiUrl` state variable:
   ```javascript
   const [apiUrl, setApiUrl] = useState('http://your-api-url:port');
   ```

### Tailwind CSS
Custom styling is defined in `src/index.css` with Tailwind's `@layer` directive:

- **Base styles**: Global body styling
- **Components**: Reusable component classes (buttons, cards, inputs)
- **Utilities**: Additional utility classes

## Usage

### Basic Query
1. Enter your legal query in the text area
2. Click "Submit Query" or press Enter
3. View the results in organized sections

### Sample Queries
Click any sample query button to quickly test the system:
- "What are the key legal issues in SCFR 531/2012?"
- "What precedents exist for writ applications?"
- "What are the constitutional rights violations?"
- "What defenses are available for public officers?"
- "How to prove Article 12(1) violations?"

### Results Display
The system displays results in organized sections:
- **Summary**: Document summaries and key points
- **Legal Issues**: Identified legal issues and precedents
- **Legal Arguments**: Generated arguments and counterarguments
- **Citations**: Verified legal citations
- **Analytics**: Pattern analysis and insights
- **Confidence Score**: Visual confidence indicator

## API Integration

The frontend communicates with the VeritasAI backend through:

- **POST** `/api/query` - Submit legal queries
- **GET** `/api/status` - Check API status
- **GET** `/health` - Health check endpoint

### Request Format
```javascript
{
  "query": "Your legal question here"
}
```

### Response Format
```javascript
{
  "summary": "Document summary...",
  "issues": "Identified legal issues...",
  "arguments": "Generated arguments...",
  "citations": "Verified citations...",
  "analytics": "Pattern analysis...",
  "confidence": 0.85
}
```

## Styling

### Color Scheme
- **Primary**: Blue (#3b82f6)
- **Success**: Green (#10b981)
- **Warning**: Yellow (#f59e0b)
- **Error**: Red (#ef4444)
- **Gray**: Various shades for text and backgrounds

### Components
- **Cards**: White background with shadow
- **Buttons**: Primary (blue) and secondary (gray) variants
- **Inputs**: Rounded borders with focus states
- **Icons**: Font Awesome icons throughout

## Development

### Adding New Features
1. Create new components in `src/components/`
2. Add new API calls in `src/services/`
3. Update styling in `src/index.css` or component files
4. Test with sample queries

### Building for Production
```bash
npm run build
```

This creates a `build/` folder with optimized production files.

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure VeritasAI backend is running on `http://localhost:8000`
   - Check CORS settings in the backend
   - Verify network connectivity

2. **Styling Issues**
   - Ensure Tailwind CSS is properly configured
   - Check that `index.css` is imported in `index.js`
   - Verify PostCSS configuration

3. **Build Errors**
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`
   - Check Node.js version compatibility
   - Verify all dependencies are installed

### Debug Mode
Enable React Developer Tools and check the browser console for detailed error messages.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is part of the VeritasAI Legal Multi-Agent System.