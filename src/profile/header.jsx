import React, {Component} from 'react';
import metadataDefinitions from './metadataDefinitions.js';


class Header extends Component {

    constructor (props) {
        super(props);
    }


    render () {

        const headerDefs = [
            'protein_name', 
            'target_terminus', 
            'uniprot_id', 
            'plate_id', 
            'well_id', 
            'hdr_all', 
            'hdr_modified', 
            'facs_grade'
        ];

        const metadataItems = metadataDefinitions.filter(
                def => headerDefs.includes(def.id)
            )
            .map(def => {
                return (
                    <MetadataItem
                        key={def.Header}
                        value={def.accessor(this.props.cellLine)}
                        label={def.Header}
                        units={def.units}
                    />
                );
            });

        return (

            <div className="flex items-center w-100 pt3 pb3">

                {/* OpenCell graphic logo */}
                <div className='flex-0-0-auto'>
                    <img src='./logos/opencell_logo.png' width={90} height={90}/>
                </div>

                {/* 'OpenCell' text header on top of the CZB logo */}
                <div className='flex-0-0-auto pl3'>
                    <div className="pb1 blue header-opencell-title">{'OpenCell'}</div>
                    <img src='./logos/logo_text_smaller.png' width={100}/>
                </div>
                
                {/* target name */}
                <div className="flex-0-0-auto pl4 blue header-target-name">
                    {this.props.cellLine.metadata?.target_name}
                </div>

                {/* target metadata items */}
                <div className='header-metadata'>
                    <ul>{metadataItems}</ul>
                </div>

                {/* target search box */}
                <div className=''>
                    <input 
                        type='text' 
                        className='header-search-textbox' 
                        defaultValue={''}
                        onKeyPress={(event) => {
                            if (event.charCode===13) {
                                this.props.onSearchChange(event.currentTarget.value);
                            }
                        }}/>
                    <div className='f7 header-search-label'>Search by target name</div>
                </div>

            </div>

        );
    }
}

function MetadataItem(props) {
    
    return (
        <li>
            <strong className='f3'>{props.value}</strong>
            <abbr className='f4' title='units description'>{props.units}</abbr>
            <div className='f5 header-metadata-label'>{props.label}</div>
        </li>
    );
}



export default Header;